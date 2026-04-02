from __future__ import annotations

"""
chat_router.py
──────────────
Page Index Chatbot — Non-RAG, deterministic document chat.

Architecture:
  1. The "Page Index" (table of contents) for the selected document is extracted
     from parsed_docs/{user_id}/{doc_id}.json and injected into the LLM system prompt.
  2. The LLM is given ONE tool: fetch_section_text(section_id).
  3. The LLM reasons about which section to read, calls the tool if needed,
     and then synthesises a grounded, citable answer.
  4. No vector embeddings — 100% deterministic section lookup.

Endpoints:
  GET  /chat                                  → chat page
  GET  /api/chat/documents                    → list all parsed documents (for selector)
  GET  /api/chat/documents/{doc_id}/index     → return section tree for a document
  POST /api/chat/query                        → ask a question about a document

BUGS FIXED:
  - api_list_chat_documents was missing `return result` at the end → returned null.
"""

import json
import os
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
import litellm

from srs_engine.core.auth.deps import require_user


router = APIRouter()

PARSED_DOCS_ROOT = Path("./parsed_docs")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_parsed_doc(user_id: str, doc_id: str) -> dict | None:
    path = PARSED_DOCS_ROOT / user_id / f"{doc_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _build_page_index(sections: list, depth: int = 0) -> str:
    """
    Recursively serialise the section tree into a compact Page Index string.
    This is injected into the LLM's system prompt as a navigation map.
    e.g.
      1 Introduction
        1.1 Purpose
        1.2 Scope
      2 System Architecture
        2.1 Components
    """
    lines = []
    indent = "  " * depth
    for s in sections:
        sid     = s.get("section_id", "?")
        heading = s.get("heading", "")
        lines.append(f"{indent}{sid} {heading}")
        lines.extend(_build_page_index(s.get("subsections", []), depth + 1).splitlines())
    return "\n".join(lines)


def _fetch_section_text(sections: list, section_id: str) -> str | None:
    """
    Tool implementation: given a section_id string (e.g. '2.1'), return
    the verbatim content of that section (and its subsections).
    Searches the entire tree recursively.
    """
    for s in sections:
        if s.get("section_id") == section_id:
            text: str = (s.get("content") or "").strip()
            # Include subsection summaries
            subs = s.get("subsections", [])
            if subs:
                for sub in subs:
                    sub_text = (sub.get("content") or "").strip()
                    if sub_text:
                        text = text + f"\n\n[{sub.get('section_id')} {sub.get('heading')}]\n{sub_text}"
            return text or "(This section has no text content.)"
        # Recurse into subsections
        found = _fetch_section_text(s.get("subsections", []), section_id)
        if found is not None:
            return found
    return None


def _render(request: Request, template: str, **ctx):
    return request.app.state.templates.TemplateResponse(
        template,
        {
            "request": request,
            "is_logged_in": bool(request.session.get("user_id")),
            "user": request.session.get("display_name"),
            **ctx,
        },
    )


# ── Page route ────────────────────────────────────────────────────────────────

@router.get("/chat")
async def chat_page(request: Request):
    """Render the Document Chat page."""
    if not request.session.get("user_id"):
        return RedirectResponse(url="/login?next=/chat", status_code=302)
    return _render(request, "pages/document_chat.html")


# ── API routes ────────────────────────────────────────────────────────────────

@router.get("/api/chat/documents")
async def api_list_chat_documents(user=Depends(require_user)):
    """
    List all parsed documents available for chatting.
    Returns [{doc_id, filename, section_count, word_count}].
    """
    user_id = str(user.get("_id"))

    # ── Sync generated documents (ensure they are parsed) ──
    from srs_engine.core.services.parse_service import parse_uploaded_file

    gen_dir = Path(f"./srs_engine/generated_srs/{user_id}")
    if gen_dir.exists():
        for docx_path in gen_dir.glob("*.docx"):
            doc_id = docx_path.stem
            json_path = PARSED_DOCS_ROOT / user_id / f"{doc_id}.json"
            if not json_path.exists():
                try:
                    await parse_uploaded_file(
                        user_id=user_id,
                        file_id=doc_id,
                        storage_path=str(docx_path),
                        original_filename=docx_path.name,
                        file_type="docx"
                    )
                except Exception:
                    continue

    user_dir = PARSED_DOCS_ROOT / user_id
    if not user_dir.exists():
        return []

    result = []
    for json_path in user_dir.glob("*.json"):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            meta = data.get("metadata", {})
            result.append({
                "doc_id":        json_path.stem,
                "filename":      meta.get("original_filename", json_path.stem),
                "section_count": len(data.get("sections", [])),
                "word_count":    meta.get("word_count", 0),
                "project_name":  meta.get("project_name", ""),
            })
        except Exception:
            continue

    # ── BUG FIX: missing return statement ──────────────────────────────────────
    # The original code built `result` but never returned it, so the endpoint
    # always returned null/None, causing the document list to be empty.
    return result


@router.get("/api/chat/documents/{doc_id}/index")
async def api_get_page_index(doc_id: str, user=Depends(require_user)):
    """
    Return the full section tree (Page Index) for a document.
    """
    user_id = str(user.get("_id"))
    data = _load_parsed_doc(user_id, doc_id)
    if not data:
        return {"error": "Document not found"}

    return data.get("sections", [])


@router.post("/api/chat/query")
async def api_chat_query(request: Request, user=Depends(require_user)):
    """
    Page Index Chatbot — single turn query.

    Request body: { "doc_id": str, "question": str, "history": [...] }
    The LLM gets the Page Index as a map and can request specific sections
    via tool calling (function call loop). Max 3 tool calls per turn to
    prevent runaway loops.
    """
    user_id = str(user.get("_id"))
    body    = await request.json()
    doc_id   = body.get("doc_id", "").strip()
    question = body.get("question", "").strip()
    history  = body.get("history", [])  # [{role, content}] for multi-turn

    if not doc_id or not question:
        return {"error": "doc_id and question are required."}

    # ── Load the parsed document ──────────────────────────────────────────────
    data = _load_parsed_doc(user_id, doc_id)
    if not data:
        return {"error": "Document not found. Please upload and parse it first."}

    meta     = data.get("metadata", {})
    sections = data.get("sections", [])
    filename = meta.get("original_filename", doc_id)

    # ── Build the Page Index map for the system prompt ────────────────────────
    page_index = _build_page_index(sections) or "(No sections detected in this document.)"

    system_prompt = f"""You are an expert document analyst chatbot. You have been given the document:
"{filename}"

Below is the complete Page Index (Table of Contents) of this document:

=== PAGE INDEX ===
{page_index}
=== END PAGE INDEX ===

INSTRUCTIONS:
1. When the user asks a question, look at the Page Index to identify the most relevant section(s).
2. If you need to read a section's full content, call the `fetch_section_text` function with the exact section_id (e.g. "2.1").
3. Use the retrieved content to give a precise, grounded answer.
4. Always cite the section you used (e.g., "According to section 2.1 Security Requirements...").
5. If you are confident the answer is in the index headings alone, answer directly without calling the function.
6. Never make up information. If the document doesn't contain the answer, say so honestly.
"""

    # ── Define the fetch_section_text tool ───────────────────────────────────
    tools = [
        {
            "type": "function",
            "function": {
                "name": "fetch_section_text",
                "description": "Fetch the full text content of a specific section from the document by its section_id.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "section_id": {
                            "type": "string",
                            "description": "The section ID to fetch (e.g. '1', '2.1', '3.4.2')",
                        }
                    },
                    "required": ["section_id"],
                },
            },
        }
    ]

    # ── Build the message list ──────────────────────────────────────────────
    messages = [{"role": "system", "content": system_prompt}]
    for h in history[-10:]:  # Keep last 10 turns for context window control
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": question})

    # ── Agentic tool-calling loop (max 3 rounds) ────────────────────────────
    model = os.environ.get("GROQ_MODEL", "groq/meta-llama/llama-4-scout-17b-16e-instruct")
    tool_calls_made = []

    for _ in range(3):  # Max 3 tool call rounds
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.1,
            max_tokens=1500,
        )

        msg = response.choices[0].message

        # No tool call — the LLM has a final answer
        if not msg.tool_calls:
            return {
                "answer":     msg.content or "",
                "tool_calls": tool_calls_made,
                "doc_id":     doc_id,
                "filename":   filename,
            }

        # Process each tool call the LLM requested
        messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": [
            {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in msg.tool_calls
        ]})

        for tc in msg.tool_calls:
            args        = json.loads(tc.function.arguments or "{}")
            section_id  = args.get("section_id", "").strip()
            section_text = _fetch_section_text(sections, section_id)

            if section_text is None:
                section_text = f"Section '{section_id}' was not found in this document. Please check the Page Index."

            tool_calls_made.append({"section_id": section_id, "chars_returned": len(section_text)})

            messages.append({
                "role":         "tool",
                "tool_call_id": tc.id,
                "content":      section_text,
            })

    # If we exhausted the loop, return what we have
    last_assistant = next((m for m in reversed(messages) if m["role"] == "assistant"), None)
    return {
        "answer":     last_assistant.get("content") or "I was unable to produce a final answer. Please try rephrasing.",
        "tool_calls": tool_calls_made,
        "doc_id":     doc_id,
        "filename":   filename,
    }