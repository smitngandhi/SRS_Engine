from __future__ import annotations

"""
diagram_service.py
──────────────────
Orchestrates the Diagram Studio pipeline:

  1. generate_mermaid_code()  → Call Groq LLM → raw Mermaid syntax
  2. render_diagram_svg()     → mmdc → SVG file on disk
  3. create_diagram()         → LLM + render + persist to MongoDB
  4. regenerate_diagram()     → LLM + render + new version in MongoDB
  5. save_edited_diagram()    → user code + render + new version
  6. get_diagram()            → load from MongoDB
  7. list_diagrams_by_project()
  8. list_recent_diagrams()
  9. delete_diagram()
"""

import os
import re
import shutil
import subprocess
import ctypes
import platform
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException
import litellm

from srs_engine.core.db.diagram_repo import DiagramRepo
from srs_engine.core.logging import get_logger
from srs_engine.schemas.diagram_schemas.diagram_schemas import DiagramOut

logger = get_logger(__name__)

# ── Storage root (filesystem) ──────────────────────────────────────────────────
DIAGRAMS_DIR = Path("./srs_engine/static/diagrams")

# ── Public URL prefix — must match app.mount("/static", ...) in main.py ───────
STATIC_URL_PREFIX = "/static/diagrams"

# ── Diagram type → Mermaid keyword mapping ─────────────────────────────────────
DIAGRAM_HEADERS = {
    "flowchart": "flowchart TD",
    "sequence": "sequenceDiagram",
    "erd": "erDiagram",
    "class": "classDiagram",
    "custom": "flowchart TD",
}

# ── System prompts per diagram type ───────────────────────────────────────────
SYSTEM_PROMPTS = {
    "flowchart": (
        "You are a Mermaid.js expert. Generate ONLY valid Mermaid flowchart syntax. "
        "Start with 'flowchart TD' or 'flowchart LR'. "
        "Use simple node IDs (A, B, C or short words). "
        "For edge labels use ONLY this format: A -->|label text| B  "
        "The label must be enclosed in single pipes with NO angle brackets, no special chars, no quotes. "
        "NEVER write -->|label|> — the closing is always | not |>. "
        "Output raw Mermaid code only — no markdown fences, no explanations."
    ),
    "sequence": (
        "You are a Mermaid.js expert. Generate ONLY valid Mermaid sequence diagram syntax. "
        "Start with 'sequenceDiagram'. "
        "Use participant declarations. "
        "IMPORTANT: Always use 'Actor->>Actor: Message' for arrows. Do NOT use flowchart arrows (like -->|text|). "
        "Output raw Mermaid code only — no markdown fences, no explanations."
    ),
    "erd": (
        "You are a Mermaid.js expert. Generate ONLY valid Mermaid ER diagram syntax. "
        "Start with 'erDiagram'. "
        "Use proper entity relationship notation. "
        "Output raw Mermaid code only — no markdown fences, no explanations."
    ),
    "class": (
        "You are a Mermaid.js expert. Generate ONLY valid Mermaid class diagram syntax. "
        "Start with 'classDiagram'. "
        "Include attributes and methods. "
        "Output raw Mermaid code only — no markdown fences, no explanations."
    ),
    "custom": (
        "You are a Mermaid.js expert. Generate ONLY valid Mermaid diagram syntax. "
        "Choose the most appropriate diagram type. "
        "Output raw Mermaid code only — no markdown fences, no explanations."
    ),
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _svg_url(user_id: str, diagram_id: str, version_number: int) -> str:
    """
    Return the PUBLIC browser URL for a diagram version SVG.
    Always uses forward slashes. This is what gets stored in MongoDB.

    e.g. /static/diagrams/user123/diag456/v2.svg
    """
    return f"{STATIC_URL_PREFIX}/{user_id}/{diagram_id}/v{version_number}.svg"


def _svg_disk_path(user_id: str, diagram_id: str, version_number: int) -> Path:
    """
    Return the filesystem Path where mmdc should write the SVG.
    Creates the directory if it does not exist.
    """
    directory = DIAGRAMS_DIR / user_id / diagram_id
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"v{version_number}.svg"


def _get_short_path(long_path: str) -> str:
    """Convert long Windows path to short 8.3 format for mmdc compatibility."""
    if platform.system() != "Windows":
        return long_path
    _GetShortPathNameW = ctypes.windll.kernel32.GetShortPathNameW
    _GetShortPathNameW.argtypes = [
        ctypes.wintypes.LPCWSTR,
        ctypes.wintypes.LPWSTR,
        ctypes.wintypes.DWORD,
    ]
    _GetShortPathNameW.restype = ctypes.wintypes.DWORD
    output_buf_size = 0
    while True:
        output_buf = ctypes.create_unicode_buffer(output_buf_size)
        needed = _GetShortPathNameW(long_path, output_buf, output_buf_size)
        if output_buf_size >= needed:
            return output_buf.value if output_buf.value else long_path
        output_buf_size = needed


def _find_mmdc() -> str:
    """Locate mmdc executable."""
    mmdc_path = shutil.which("mmdc")
    if not mmdc_path and platform.system() == "Windows":
        npm_mmdc = os.path.join(os.environ.get("APPDATA", ""), "npm", "mmdc.CMD")
        if os.path.exists(npm_mmdc):
            mmdc_path = npm_mmdc
    if not mmdc_path:
        raise FileNotFoundError(
            "mmdc not found. Install with: npm install -g @mermaid-js/mermaid-cli"
        )
    if platform.system() == "Windows":
        mmdc_path = _get_short_path(mmdc_path)
    return mmdc_path


def _sanitize_mermaid(text: str, diagram_type: str) -> str:
    text = text.strip()

    # ── Remove markdown fences ─────────────────────────────────────────────────
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)

    # ── Remove HTML tags ───────────────────────────────────────────────────────
    text = re.sub(r"<[^>]+>", "", text)

    # ── Normalize multi-dash arrows ────────────────────────────────────────────
    text = re.sub(r"-{3,}>", "-->", text)
    text = re.sub(r"==>", "-->", text)

    # ── FIX: Remove stray '>' after closing pipe in edge labels ───────────────
    #    e.g.  -->|submits credentials|> Frontend  →  -->|submits credentials| Frontend
    text = re.sub(r"\|([^|\n]*)\|>", r"|\1|", text)

    # ── FIX: Sanitize characters inside pipe labels that break the parser ──────
    def _clean_label(m: re.Match) -> str:
        label = m.group(1)
        label = label.replace("<", "").replace(">", "").replace("`", "").replace('"', "'")
        return f"|{label}|"

    text = re.sub(r"\|([^|\n]+)\|", _clean_label, text)

    # ── Fix sequence diagram arrows ────────────────────────────────────────────
    if diagram_type == "sequence":
        text = re.sub(r"-->|->", "->>", text)

    # ── Ensure valid header ────────────────────────────────────────────────────
    expected_header = DIAGRAM_HEADERS.get(diagram_type, "flowchart TD")
    lines = text.splitlines()

    if not lines or not any(
        lines[0].startswith(h)
        for h in ["flowchart", "graph", "sequenceDiagram", "erDiagram", "classDiagram"]
    ):
        lines.insert(0, expected_header)

    # ── Fix unclosed brackets (basic safety) ──────────────────────────────────
    fixed_lines = []
    for line in lines:
        if "[" in line and "]" not in line:
            line += "]"
        fixed_lines.append(line)

    return "\n".join(fixed_lines)


def _render_svg(mermaid_code: str, disk_path: Path) -> None:
    """Render Mermaid code to SVG using mmdc. Writes to disk_path."""
    disk_path.parent.mkdir(parents=True, exist_ok=True)
    mmd_path = disk_path.with_suffix(".mmd")

    with open(mmd_path, "w", encoding="utf-8") as f:
        f.write(mermaid_code)

    mmdc = _find_mmdc()
    cmd = [mmdc, "-i", str(mmd_path), "-o", str(disk_path)]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(f"diagram_service | SVG rendered | disk_path={disk_path}")
        if result.stdout:
            logger.debug(f"diagram_service | mmdc stdout | {result.stdout}")
    except subprocess.CalledProcessError as e:
        logger.error(f"diagram_service | mmdc error | stderr={e.stderr} | stdout={e.stdout}")
        raise HTTPException(status_code=500, detail=f"Diagram rendering failed: {e.stderr}")


# ── LLM call ──────────────────────────────────────────────────────────────────

async def generate_mermaid_code(
    prompt: str,
    diagram_type: str,
    project_name: str,
    context_str: str = "",
    error_feedback: str = "",
) -> str:
    """
    Call Groq LLM to generate Mermaid syntax from a natural-language prompt.

    context_str  – structured Page-Index text built by the router from selected docs.
    error_feedback – previous Mermaid parse error (used for retry attempts).
    """
    system_prompt = SYSTEM_PROMPTS.get(diagram_type, SYSTEM_PROMPTS["custom"])

    # ── Build user message sections ───────────────────────────────────────────
    parts = [
        f"Project: {project_name}",
        f"Diagram type: {diagram_type}",
    ]

    if context_str:
        parts.append(context_str)

    parts.append(f"Requirement: {prompt}")

    if error_feedback:
        parts.append(
            f"\n⚠️ IMPORTANT: Your previous attempt had this Mermaid parse error:\n"
            f"{error_feedback}\n"
            f"Fix the syntax issue and return corrected Mermaid code only."
        )

    parts.append("\nGenerate the Mermaid diagram code now.")
    user_message = "\n".join(parts)

    model = os.environ.get("GROQ_MODEL", "groq/meta-llama/llama-4-scout-17b-16e-instruct")

    try:
        response = await litellm.acompletion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
            max_tokens=2048,
        )
        raw = response.choices[0].message.content or ""
        logger.debug(f"diagram_service | LLM raw output | {raw}")
        sanitized = _sanitize_mermaid(raw, diagram_type)
        logger.debug(f"diagram_service | sanitized output | {sanitized}")
        return sanitized
    except Exception as e:
        logger.error(f"diagram_service | LLM error | {str(e)}")
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {str(e)}")


# ── Public service functions ──────────────────────────────────────────────────

async def create_diagram(
    db: Any,
    user_id: str,
    project_name: str,
    prompt: str,
    diagram_type: str,
    context_str: str = "",
    error_feedback: str = "",
) -> DiagramOut:
    """Generate + render + persist a new diagram."""
    mermaid_code = await generate_mermaid_code(
        prompt, diagram_type, project_name,
        context_str=context_str,
        error_feedback=error_feedback,
    )

    repo = DiagramRepo(db)

    # Use a temp ID so we know the disk path before the DB insert
    temp_diagram_id = str(uuid.uuid4())
    disk_path = _svg_disk_path(user_id, temp_diagram_id, 1)
    _render_svg(mermaid_code, disk_path)

    # Store the PUBLIC URL — never a raw filesystem path
    temp_svg_url = _svg_url(user_id, temp_diagram_id, 1)

    diagram_id = await repo.create_diagram(
        user_id=user_id,
        project_name=project_name,
        diagram_type=diagram_type,
        prompt=prompt,
        mermaid_code=mermaid_code,
        svg_path=temp_svg_url,
    )

    # If the repo assigned a different ID, rename directory and fix stored URL
    if temp_diagram_id != diagram_id:
        temp_dir = DIAGRAMS_DIR / user_id / temp_diagram_id
        actual_dir = DIAGRAMS_DIR / user_id / diagram_id
        if temp_dir.exists():
            temp_dir.rename(actual_dir)

        actual_svg_url = _svg_url(user_id, diagram_id, 1)
        await db.diagrams.update_one(
            {"diagram_id": diagram_id},
            {"$set": {"versions.0.svg_path": actual_svg_url}},
        )

    doc = await repo.get_diagram(user_id, diagram_id)
    return DiagramOut.from_doc(doc)


async def regenerate_diagram(
    db: Any,
    user_id: str,
    diagram_id: str,
    prompt: str,
    diagram_type: str,
    context_str: str = "",
    error_feedback: str = "",
) -> DiagramOut:
    """Generate a new version from a new prompt and add it to the existing diagram."""
    repo = DiagramRepo(db)
    existing = await repo.get_diagram(user_id, diagram_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Diagram not found")

    mermaid_code = await generate_mermaid_code(
        prompt, diagram_type, existing["project_name"],
        context_str=context_str,
        error_feedback=error_feedback,
    )
    version_number = len(existing["versions"]) + 1

    disk_path = _svg_disk_path(user_id, diagram_id, version_number)
    _render_svg(mermaid_code, disk_path)

    svg_url = _svg_url(user_id, diagram_id, version_number)

    await repo.add_version(
        user_id=user_id,
        diagram_id=diagram_id,
        prompt=prompt,
        mermaid_code=mermaid_code,
        svg_path=svg_url,
    )

    doc = await repo.get_diagram(user_id, diagram_id)
    return DiagramOut.from_doc(doc)


async def save_edited_diagram(
    db: Any, user_id: str, diagram_id: str, mermaid_code: str
) -> DiagramOut:
    """Save manually edited Mermaid code as a new version (no LLM call)."""
    repo = DiagramRepo(db)
    existing = await repo.get_diagram(user_id, diagram_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Diagram not found")

    clean_code = _sanitize_mermaid(mermaid_code, existing.get("diagram_type", "custom"))
    version_number = len(existing["versions"]) + 1

    disk_path = _svg_disk_path(user_id, diagram_id, version_number)
    _render_svg(clean_code, disk_path)

    svg_url = _svg_url(user_id, diagram_id, version_number)

    last_prompt = existing["versions"][-1]["prompt"] if existing["versions"] else "Manual edit"
    await repo.add_version(
        user_id=user_id,
        diagram_id=diagram_id,
        prompt=f"[edited] {last_prompt}",
        mermaid_code=clean_code,
        svg_path=svg_url,
    )

    doc = await repo.get_diagram(user_id, diagram_id)
    return DiagramOut.from_doc(doc)


async def get_diagram(db: Any, user_id: str, diagram_id: str) -> DiagramOut:
    repo = DiagramRepo(db)
    doc = await repo.get_diagram(user_id, diagram_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Diagram not found")
    return DiagramOut.from_doc(doc)


async def list_diagrams_by_project(
    db: Any, user_id: str, project_name: str
) -> list[DiagramOut]:
    repo = DiagramRepo(db)
    docs = await repo.list_by_project(user_id, project_name)
    return [DiagramOut.from_doc(d) for d in docs]


async def list_recent_diagrams(db: Any, user_id: str) -> list[DiagramOut]:
    repo = DiagramRepo(db)
    docs = await repo.list_recent(user_id, limit=6)
    return [DiagramOut.from_doc(d) for d in docs]


async def list_user_projects(db: Any, user_id: str) -> list[str]:
    """Return all project names that have diagrams for this user."""
    repo = DiagramRepo(db)
    return await repo.list_projects(user_id)


async def delete_diagram(db: Any, user_id: str, diagram_id: str) -> bool:
    repo = DiagramRepo(db)
    deleted = await repo.delete_diagram(user_id, diagram_id)
    if deleted:
        diagram_dir = DIAGRAMS_DIR / user_id / diagram_id
        if diagram_dir.exists():
            import shutil as _shutil
            _shutil.rmtree(diagram_dir, ignore_errors=True)
    return deleted