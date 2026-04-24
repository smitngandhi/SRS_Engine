from __future__ import annotations

"""
core/routers/chat_router.py  v3
────────────────────────────────
Page-Index Chatbot — uses the existing PAGE_INDEX_MAP + _sections.json +
FAISS search_section() exactly as already built by generate_srs().

Architecture:
  1. GET /api/chat/documents
       Scans generated_srs/{user_id}/ for *_sections.json files.
       Returns doc list where doc_id == project_name.

  2. GET /api/chat/documents/{doc_id}/index
       Loads {project_name}_sections.json.
       Builds the TOC tree from PAGE_INDEX_MAP so page_index values (10, 20 …)
       become section_ids.  Sub-keys of each section dict become subsections.

  3. POST /api/chat/query
       Phase 1 — Tool-calling loop (max 3 rounds).
         LLM tool: fetch_section(section_key)
           e.g. fetch_section("introduction_section")
           → reads sections_json[section_key] → readable text.
       Phase 2 — RAG fallback (search_section from srs_rag_index).
         Triggered when: no tool called, answer is short, or weak-signal phrases.
         search_section(query, user_id, project_name) → (section_key, confidence)
         → reads sections_json[section_key] for synthesis.

BUGS FIXED vs. v1/v2:
  BUG-1  api_list_chat_documents() never returned result → always null.
  BUG-2  Used parsed_docs/ instead of generated_srs/*_sections.json.
  BUG-3  RAG index built but never queried (wrong function name).
  BUG-4  doc_id was a random hash; now == project_name.
  BUG-5  RAG fallback never triggered.
  NEW    Uses PAGE_INDEX_MAP (already computed at generation time) instead of
         ad-hoc tree reconstruction.
  NEW    Uses search_section() — the real function in srs_rag_index.py —
         instead of the non-existent query_rag_index().
"""

import json
import os
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
import litellm

from srs_engine.core.auth.deps import require_user
from srs_engine.core.db.mongo import get_db
from srs_engine.core.db.quota_repo import QuotaRepo

router = APIRouter()


# Human-readable labels for each section_key
_SECTION_LABELS: dict[str, str] = {
    "introduction_section":        "Introduction",
    "overall_description_section": "Overall Description",
    "system_features_section":     "System Features",
    "external_interfaces_section": "External Interfaces",
    "nfr_section":                 "Non-Functional Requirements",
    "glossary_section":            "Glossary",
    "assumptions_section":         "Assumptions & Dependencies",
}

# Keys to skip when building subsection trees (metadata, not content)
_SKIP_KEYS = frozenset({"section_id", "section_number", "domain", "project_name"})

# Phrases that signal a weak/failed LLM answer
_WEAK_SIGNALS = (
    "don't know", "cannot find", "not mentioned", "not found",
    "no information", "unable to find", "not specified",
    "not contain", "not available",
)


# ── File I/O (GridFS via Service) ─────────────────────────────────────────────

async def _load_sections_json(user_id: str, project_name: str, db: Any) -> dict | None:
    """Fetch sections from GridFS."""
    from srs_engine.core.db.file_storage import FileStorage
    fs = FileStorage(db)
    data = await fs.get_file({"type": "sections_json", "user_id": user_id, "project_name": project_name})
    if not data:
        return None
    try:
        return json.loads(data)
    except Exception:
        return None


async def _load_meta_json(user_id: str, project_name: str, db: Any) -> dict:
    """Fetch metadata from GridFS."""
    from srs_engine.core.db.file_storage import FileStorage
    fs = FileStorage(db)
    data = await fs.get_file({"type": "meta_json", "user_id": user_id, "project_name": project_name})
    if not data:
        return {}
    try:
        return json.loads(data)
    except Exception:
        return {}


# ── Section content → readable text for LLM ──────────────────────────────────

def _to_text(obj, depth: int = 0, max_depth: int = 5) -> str:
    """
    Recursively convert a section value (dict / list / str / …) into
    indented, human-readable plain text the LLM can reason over.
    """
    if depth >= max_depth:
        return str(obj)[:300]

    indent = "  " * depth

    if isinstance(obj, str):
        return obj.strip()

    if isinstance(obj, (int, float, bool)):
        return str(obj)

    if isinstance(obj, list):
        parts = []
        for i, item in enumerate(obj, 1):
            rendered = _to_text(item, depth + 1, max_depth)
            if rendered:
                parts.append(f"{indent}  {i}. {rendered}")
        return "\n".join(parts)

    if isinstance(obj, dict):
        parts = []
        for k, v in obj.items():
            if k in _SKIP_KEYS:
                continue
            label = k.replace("_", " ").title()
            rendered = _to_text(v, depth + 1, max_depth)
            if rendered:
                parts.append(f"{indent}{label}:\n{indent}  {rendered}")
        return "\n".join(parts)

    return repr(obj)


def _section_readable(section_data) -> str:
    """Full readable dump of a section for the LLM tool response."""
    text = _to_text(section_data)
    # Cap at ~4 000 chars to stay within LLM context window comfortably
    if len(text) > 4000:
        text = text[:4000] + "\n\n[… content truncated …]"
    return text or "(No content available for this section.)"


# ── TOC tree builder (uses PAGE_INDEX_MAP) ────────────────────────────────────

def _build_toc_tree(sections_json: dict, domain: str = "technical") -> list[dict]:
    """
    Build the section tree that the frontend renders as the clickable TOC.

    Uses PAGE_INDEX_MAP so the tree reflects the exact ordering and labels
    already defined for the domain — no guesswork.

    Tree node schema:
        {
            "section_id":  str,   # page_index as string: "10", "20" …
            "section_key": str,   # "introduction_section" etc.
            "heading":     str,   # Human label
            "content":     str,   # First ~300 chars for the preview pane
            "subsections": list,  # Sub-keys of the section dict
        }
    """
    try:
        from srs_engine.utils.page_index_map import get_all_sections
        entries = get_all_sections(domain)
    except Exception:
        # Graceful fallback: build ordering from _SECTION_LABELS
        entries = [
            {"page_index": i * 10, "section_key": k, "section_type": "text"}
            for i, k in enumerate(_SECTION_LABELS, 1)
        ]

    tree: list[dict] = []
    for entry in entries:
        page_idx    = entry["page_index"]           # 10, 20, 30 …
        section_key = entry["section_key"]           # "introduction_section"
        section_data = sections_json.get(section_key)
        if not section_data:
            continue

        heading = _SECTION_LABELS.get(section_key, section_key.replace("_", " ").title())

        # Build subsections from the immediate child keys of the section dict
        subsections: list[dict] = []
        if isinstance(section_data, dict):
            sub_idx = 1
            for sub_key, sub_val in section_data.items():
                if sub_key in _SKIP_KEYS:
                    continue
                sub_heading = sub_key.replace("_", " ").title()
                sub_content = _to_text(sub_val, depth=0, max_depth=1)[:300]
                subsections.append({
                    "section_id":  f"{page_idx}.{sub_idx}",
                    "section_key": section_key,       # parent key — used for fetch
                    "sub_key":     sub_key,
                    "heading":     sub_heading,
                    "content":     sub_content,
                    "subsections": [],
                })
                sub_idx += 1
        elif isinstance(section_data, list):
            for i, item in enumerate(section_data, 1):
                if isinstance(item, dict):
                    sub_heading = (
                        item.get("name") or item.get("title") or
                        item.get("feature_name") or item.get("term") or
                        f"Item {i}"
                    )
                    sub_content = _to_text(item, depth=0, max_depth=1)[:300]
                    subsections.append({
                        "section_id":  f"{page_idx}.{i}",
                        "section_key": section_key,
                        "sub_key":     None,
                        "heading":     str(sub_heading)[:80],
                        "content":     sub_content,
                        "subsections": [],
                    })

        # Top-level preview: first 300 chars of the section
        top_content = _to_text(section_data, depth=0, max_depth=1)[:300]

        tree.append({
            "section_id":  str(page_idx),
            "section_key": section_key,
            "heading":     heading,
            "content":     top_content,
            "subsections": subsections,
            "section_type": entry.get("section_type", "text"),
        })

    return tree


# ── Page-Index string (injected into LLM system prompt) ──────────────────────

def _build_page_index_string(tree: list[dict]) -> str:
    """
    Build the compact Page Index string the LLM receives as its navigation map.

    Format:
        10  Introduction                (key: introduction_section)
          10.1  Purpose
          10.2  Scope
        20  Overall Description         (key: overall_description_section)
          ...
    """
    lines: list[str] = []
    for node in tree:
        sid  = node["section_id"]
        key  = node["section_key"]
        head = node["heading"]
        lines.append(f"{sid}  {head}  (key: {key})")
        for sub in node.get("subsections") or []:
            lines.append(f"  {sub['section_id']}  {sub['heading']}")
    return "\n".join(lines)


# ── Precise section lookup (LLM tool implementation) ─────────────────────────

def _fetch_section(sections_json: dict, section_key: str) -> str:
    """
    Tool implementation: given section_key, return the readable content.
    Supports both top-level keys ("introduction_section") and
    sub-key references ("introduction_section.purpose" notation).
    """
    if "." in section_key:
        parts = section_key.split(".", 1)
        top_key = parts[0]
        sub_key = parts[1]
        top_data = sections_json.get(top_key)
        if isinstance(top_data, dict) and sub_key in top_data:
            return _section_readable(top_data[sub_key])
        # Fall through to full section
        section_key = top_key

    data = sections_json.get(section_key)
    if data is None:
        return (
            f"Section key '{section_key}' not found. "
            f"Valid keys: {', '.join(k for k in _SECTION_LABELS if sections_json.get(k))}"
        )
    return _section_readable(data)


# ── RAG fallback (uses the real search_section from srs_rag_index) ────────────

def _rag_search(
    user_id: str,
    project_name: str,
    query: str,
    sections_json: dict,
) -> tuple[str | None, str, float]:
    """
    Query the FAISS index via search_section().
    Returns (section_key, readable_content, confidence).
    Returns (None, "", 0.0) on any error.
    """
    try:
        from srs_engine.utils.srs_rag_index import search_section
        section_key, confidence = search_section(
            query=query,
            user_id=user_id,
            project_name=project_name,
            top_k=1,
        )
        if not section_key or confidence < 0.25:
            return None, "", confidence
        content = _fetch_section(sections_json, section_key)
        return section_key, content, confidence
    except FileNotFoundError:
        return None, "", 0.0          # RAG index not built yet — silent skip
    except Exception:
        return None, "", 0.0          # Any other error — graceful degradation


# ── Template helper ────────────────────────────────────────────────────────────

def _render(request: Request, template: str, **ctx):
    return request.app.state.templates.TemplateResponse(
        template,
        {
            "request":      request,
            "is_logged_in": bool(request.session.get("user_id")),
            "user":         request.session.get("display_name"),
            **ctx,
        },
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/chat")
async def chat_page(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/login?next=/chat", status_code=302)
    return _render(request, "pages/document_chat.html")


# ── List documents ────────────────────────────────────────────────────────────

@router.get("/api/chat/documents")
async def api_list_chat_documents(user=Depends(require_user), db=Depends(get_db)):
    """
    List all SRS projects from GridFS.
    """
    from srs_engine.core.services.generated_srs_upgrade_service import list_generated_srs
    user_id = str(user.get("_id"))
    
    # Use the existing service that already pulls from GridFS
    docs = await list_generated_srs(user_id, db)
    print(f"[chat_router] list_generated_srs for {user_id} returned {len(docs)} docs")
    
    result = []
    for doc in docs:
        project_name = doc.get("project_name", "")
        if not project_name:
            continue
            
        result.append({
            "doc_id":        project_name,
            "filename":      f"{project_name} — SRS",
            "project_name":  project_name,
            "domain":        doc.get("domain", "technical"),
            "section_count": len(doc.get("modified_sections", [])), # Approximation
            "organization":  doc.get("organization", ""),
            "generated_at":  doc.get("generated_at", ""),
        })

    print(f"[chat_router] returning {len(result)} formatted docs")
    return result


# ── Section tree ──────────────────────────────────────────────────────────────

@router.get("/api/chat/documents/{doc_id}/index")
async def api_get_page_index(doc_id: str, user=Depends(require_user), db=Depends(get_db)):
    """
    Return the full section tree for a project.
    doc_id == project_name.
    """
    user_id       = str(user.get("_id"))
    sections_json = await _load_sections_json(user_id, doc_id, db)
    if sections_json is None:
        return {"error": f"No generated SRS found for project '{doc_id}'."}

    domain = sections_json.get("domain", "technical")
    tree   = _build_toc_tree(sections_json, domain)
    if not tree:
        return {"error": "SRS sections are empty or malformed."}
    return tree


# ── Chat query ────────────────────────────────────────────────────────────────

@router.post("/api/chat/query")
async def api_chat_query(
    request: Request, 
    user=Depends(require_user),
    db=Depends(get_db)
):
    """
    Page-Index chatbot — tool calling + RAG fallback.

    Request body:
        { "doc_id": str, "question": str, "history": [{role, content}, …] }

    Flow:
      Phase 1 — LLM tool-calling loop (max 3 rounds).
        Tool: fetch_section(section_key) reads sections_json[section_key].
      Phase 2 — RAG fallback via search_section() from srs_rag_index.
        Triggers when answer is weak.  Fetches the highest-confidence section,
        injects it as context, and calls a synthesis completion.

    BUG-3 FIX: search_section() (the real function) is now called.
    BUG-5 FIX: RAG fallback triggers correctly.
    NEW:   LLM tool uses section_key (not numeric id) for precise lookup.
    """
    user_id  = str(user.get("_id"))
    body     = await request.json()
    doc_id   = body.get("doc_id", "").strip()   # == project_name
    question = body.get("question", "").strip()
    history  = body.get("history", [])

    if not doc_id or not question:
        return {"error": "doc_id and question are required."}

    # ── Quota Check ───────────────────────────────────────────────────────────
    quota = QuotaRepo(db)
    chat_limit = user.get("custom_chat_query_limit", 15)
    if not await quota.check_quota(user_id, "chat_query_count", limit=chat_limit):
        return {
            "error": f"Chat quota reached ({chat_limit}/{chat_limit} messages). Upgrade your plan to continue chatting with your documents!"
        }

    # ── Load ──────────────────────────────────────────────────────────────────
    sections_json = await _load_sections_json(user_id, doc_id, db)
    if sections_json is None:
        return {"error": f"SRS document '{doc_id}' not found. Generate it first."}

    domain = sections_json.get("domain", "technical")
    tree   = _build_toc_tree(sections_json, domain)
    if not tree:
        return {"error": "Document has no readable sections."}

    page_index_str = _build_page_index_string(tree)

    # ── System prompt ─────────────────────────────────────────────────────────
    system_prompt = f"""You are a precise SRS analyst answering questions about the Software Requirements Specification for project: "{doc_id}".

The document uses these section keys:
{chr(10).join(f'  {k}' for k in _SECTION_LABELS if sections_json.get(k))}

=== PAGE INDEX ===
{page_index_str}
=== END PAGE INDEX ===

INSTRUCTIONS:
1. Identify the most relevant section from the Page Index.
2. Call fetch_section with its section_key (e.g. "system_features_section") to read its content.
3. Answer precisely using the fetched content. Always cite the section.
4. You may call fetch_section up to 3 times if multiple sections are relevant.
5. If the Page Index headings alone answer the question, answer directly.
6. Never fabricate information. If the document lacks an answer, say so explicitly."""

    # ── Tool definition ────────────────────────────────────────────────────────
    tools = [
        {
            "type": "function",
            "function": {
                "name": "fetch_section",
                "description": (
                    "Fetch the full content of a section from the SRS document. "
                    "Use the section_key shown in the Page Index, e.g. 'introduction_section', "
                    "'system_features_section', 'nfr_section'."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "section_key": {
                            "type": "string",
                            "description": "The section key to fetch (e.g. 'system_features_section')",
                        }
                    },
                    "required": ["section_key"],
                },
            },
        }
    ]

    # ── Messages ───────────────────────────────────────────────────────────────
    messages = [{"role": "system", "content": system_prompt}]
    for h in history[-10:]:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": question})

    model = os.environ.get("GROQ_MODEL", "groq/meta-llama/llama-4-scout-17b-16e-instruct")

    tool_calls_made: list[dict] = []
    any_tool_called = False
    final_answer    = ""

    # ── Phase 1: Tool-calling loop ─────────────────────────────────────────────
    for _ in range(3):
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.1,
            max_tokens=1500,
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            final_answer = msg.content or ""
            break

        # Append assistant turn with tool calls
        any_tool_called = True
        messages.append({
            "role":       "assistant",
            "content":    msg.content or "",
            "tool_calls": [
                {
                    "id":       tc.id,
                    "type":     "function",
                    "function": {
                        "name":      tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ],
        })

        for tc in msg.tool_calls:
            args        = json.loads(tc.function.arguments or "{}")
            section_key = args.get("section_key", "").strip()
            content     = _fetch_section(sections_json, section_key)

            # Map section_key → page_index for TOC highlighting
            page_idx_str = _key_to_page_index(section_key, tree)

            tool_calls_made.append({
                "section_id":     page_idx_str,   # for TOC highlight in JS
                "section_key":    section_key,
                "chars_returned": len(content),
            })

            messages.append({
                "role":         "tool",
                "tool_call_id": tc.id,
                "content":      content,
            })
    else:
        # Loop exhausted without a final non-tool response
        last = next((m for m in reversed(messages) if m.get("role") == "assistant"), None)
        final_answer = (last or {}).get("content") or ""

    # ── Phase 2: RAG fallback ──────────────────────────────────────────────────
    answer_lower = (final_answer or "").lower()
    answer_weak  = (
        not any_tool_called
        or len(final_answer) < 120
        or any(sig in answer_lower for sig in _WEAK_SIGNALS)
    )

    rag_section_key: str | None = None
    rag_used = False

    if answer_weak:
        rag_key, rag_content, rag_confidence = _rag_search(
            user_id, doc_id, question, sections_json
        )
        if rag_key and rag_content:
            rag_section_key = rag_key
            rag_used        = True
            rag_page_idx    = _key_to_page_index(rag_key, tree)

            # Synthesis with RAG context
            synth_messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"{question}\n\n"
                        f"The following content was found via semantic search "
                        f"(section: {rag_key}, confidence: {rag_confidence:.0%}):\n\n"
                        f"{rag_content}\n\n"
                        f"Please use this content to give a complete, cited answer."
                    ),
                },
            ]
            synth_resp = await litellm.acompletion(
                model=model,
                messages=synth_messages,
                temperature=0.1,
                max_tokens=1500,
            )
            final_answer = synth_resp.choices[0].message.content or final_answer

            tool_calls_made.append({
                "section_id":     rag_page_idx,
                "section_key":    rag_key,
                "chars_returned": len(rag_content),
                "source":         "rag",
                "confidence":     round(rag_confidence, 3),
            })

    # ── Increment Quota ───────────────────────────────────────────────────────
    await quota.increment_quota(user_id, "chat_query_count")

    return {
        "answer":     final_answer or "I could not find a relevant answer in this document.",
        "tool_calls": tool_calls_made,
        "doc_id":     doc_id,
        "filename":   f"{doc_id} — SRS",
        "rag_used":   rag_used,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _key_to_page_index(section_key: str, tree: list[dict]) -> str:
    """
    Given a section_key like 'system_features_section', return the
    page_index string ('30') used as section_id in the TOC tree.
    Falls back to the section_key itself if not found.
    """
    # Strip sub-key suffix if present (e.g. "introduction_section.purpose")
    top_key = section_key.split(".")[0]
    for node in tree:
        if node.get("section_key") == top_key:
            return node["section_id"]
    return section_key