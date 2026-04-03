from __future__ import annotations

"""
core/services/diagram_service.py
─────────────────────────────────
Orchestrates the Diagram Studio pipeline.

v4 changes vs v3:
  · _sanitize_mermaid() now has a dedicated sub-function per diagram type
  · _verify_mermaid_syntax() extended with per-type pattern checks
  · SYSTEM_PROMPTS tightened with explicit "NEVER" rules per type
  · Mindmap: strip ::icon()+shape combos, bare trailing [shape] tokens
  · Sequence: handle -->, ->, ->>> arrow variants comprehensively
  · Flowchart: strip stray HTML, fix unbalanced parens/brackets/braces
  · ERD: enforce quoted relationship labels
  · Class: fix namespace/bracket mismatches
  · State: guard against flowchart arrows leaking in
  · Gantt: enforce dateFormat line, strip invalid task status tokens
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
from typing import Any, Tuple

from fastapi import HTTPException
import litellm

from srs_engine.core.db.diagram_repo import DiagramRepo
from srs_engine.core.logging import get_logger
from srs_engine.schemas.diagram_schemas.diagram_schemas import DiagramOut

logger = get_logger(__name__)

# ── Storage ────────────────────────────────────────────────────────────────────
DIAGRAMS_DIR = Path("./srs_engine/static/diagrams")
STATIC_URL_PREFIX = "/static/diagrams"

# ── Model ──────────────────────────────────────────────────────────────────────
_DEFAULT_MODEL = "groq/llama-3.3-70b-versatile"
SERVER_RETRY_LIMIT = 2

# ── Diagram types ──────────────────────────────────────────────────────────────
DIAGRAM_HEADERS = {
    "flowchart": "flowchart TD",
    "sequence":  "sequenceDiagram",
    "erd":       "erDiagram",
    "class":     "classDiagram",
    "state":     "stateDiagram-v2",
    "gantt":     "gantt",
    "mindmap":   "mindmap",
    "custom":    "flowchart TD",
}

DIAGRAM_LABELS = {
    "flowchart": "System / Process Flow",
    "sequence":  "API / Service Interaction",
    "erd":       "Database Schema (ERD)",
    "class":     "Object Model / Architecture",
    "state":     "State Machine / Lifecycle",
    "gantt":     "Project / Sprint Timeline",
    "mindmap":   "Feature / Requirement Map",
    "custom":    "Auto-select Best Type",
}

_DETAIL_INSTRUCTIONS: dict[str, str] = {
    "brief": (
        "Keep the diagram BRIEF — 5 to 10 nodes/entities maximum. "
        "Show only the top-level components and the most important connections. "
        "Omit edge labels unless critical. Prioritise clarity over completeness."
    ),
    "standard": (
        "Use STANDARD detail — 10 to 20 nodes/entities. "
        "Include main components, key relationships, and important edge labels. "
        "Balance readability and information density."
    ),
    "detailed": (
        "Use DETAILED notation — 20 to 40 nodes/entities. "
        "Include sub-components, all significant relationships, typed edges, "
        "and error/alternative paths where relevant."
    ),
    "comprehensive": (
        "Generate a COMPREHENSIVE diagram — 40+ nodes/entities if needed. "
        "Cover all components, sub-systems, edge cases, error paths, and annotations. "
        "Add notes/comments inside the diagram where clarification helps."
    ),
}

# ── System prompts per diagram type ───────────────────────────────────────────
_BASE_RULES = (
    "Output ONLY valid Mermaid syntax — no markdown fences (```), no explanations, "
    "no prose before or after the code. The very first line must be the diagram header."
)

_REASONING_GUIDE = (
    "Before writing the diagram, silently reason about:\n"
    "1. What entities/nodes/actors exist\n"
    "2. What relationships or flows connect them\n"
    "3. Which Mermaid syntax rules apply\n"
    "4. Ensure arrows and syntax match the diagram type\n"
    "Do NOT output this reasoning — output only the final Mermaid diagram."
)

SYSTEM_PROMPTS: dict[str, str] = {

"flowchart": (
f"""
You are a Mermaid.js expert specialising in flowcharts.

{_BASE_RULES}

Internal reasoning guide (DO NOT OUTPUT):
{_REASONING_GUIDE}

Rules:
· Start with 'flowchart TD' or 'flowchart LR'
· Use concise node IDs (A, B, C or short words)
· Edge labels use pipes: A -->|label| B
· NEVER use ---> or -> or ->>
· NEVER use HTML tags
· Use subgraph ... end to group nodes

Few-shot Examples

Example 1

User Request:
User authentication process

Reasoning (hidden):
User enters credentials → system validates → success or failure branch

Correct Output:
flowchart TD
A[User Login] --> B[Validate Credentials]
B -->|Valid| C[Grant Access]
B -->|Invalid| D[Show Error]

Example 2

User Request:
Order processing system

Reasoning (hidden):
Customer places order → payment → inventory check → shipping

Correct Output:
flowchart TD
A[Customer Places Order] --> B[Process Payment]
B --> C[Check Inventory]
C -->|Available| D[Ship Order]
C -->|Out of Stock| E[Notify Customer]
"""
),

"sequence": (
f"""
You are a Mermaid.js expert specialising in sequence diagrams.

{_BASE_RULES}

Internal reasoning guide (DO NOT OUTPUT):
{_REASONING_GUIDE}

Rules:
· Start with 'sequenceDiagram'
· Declare actors with participant or actor
· Request arrow: ->>
· Response arrow: -->>
· NEVER use flowchart arrows (-->, ->)

Few-shot Examples

Example 1

User Request:
User login API flow

Reasoning (hidden):
User → frontend → backend → database → response

Correct Output:
sequenceDiagram
actor User
participant Frontend
participant Backend
participant DB

User->>Frontend: Enter credentials
Frontend->>Backend: Login request
Backend->>DB: Validate user
DB-->>Backend: User valid
Backend-->>Frontend: Auth token
Frontend-->>User: Login success

Example 2

User Request:
Payment service interaction

Correct Output:
sequenceDiagram
actor Customer
participant App
participant PaymentGateway

Customer->>App: Initiate payment
App->>PaymentGateway: Charge card
PaymentGateway-->>App: Payment status
App-->>Customer: Confirmation
"""
),

"erd": (
f"""
You are a Mermaid.js expert specialising in ER diagrams.

{_BASE_RULES}

Internal reasoning guide (DO NOT OUTPUT):
{_REASONING_GUIDE}

Rules:
· Start with 'erDiagram'
· Relationships MUST include quoted label
· Use valid cardinality tokens only

Few-shot Examples

Example

User Request:
User and Order database

Correct Output:
erDiagram
USER ||--o{{ ORDER : "places"
USER {{
    int id PK
    string name
    string email
}}
ORDER {{
    int id PK
    date created_at
}}
"""
),

"class": (
f"""
You are a Mermaid.js expert specialising in class diagrams.

{_BASE_RULES}

Internal reasoning guide (DO NOT OUTPUT):
{_REASONING_GUIDE}

Rules:
· Start with 'classDiagram'
· Attributes: +type name
· Methods: +method()

Few-shot Example

User Request:
Vehicle inheritance

Correct Output:
classDiagram
Vehicle <|-- Car
Vehicle <|-- Bike

class Vehicle {{
  +start()
  +stop()
}}

class Car {{
  +openTrunk()
}}

class Bike {{
  +kickStart()
}}
"""
),

"state": (
f"""
You are a Mermaid.js expert specialising in state diagrams.

{_BASE_RULES}

Internal reasoning guide (DO NOT OUTPUT):
{_REASONING_GUIDE}

Rules:
· Start with 'stateDiagram-v2'
· Initial state is [*]
· Transitions use --> with event labels

Few-shot Example

User Request:
Order lifecycle

Correct Output:
stateDiagram-v2
[*] --> Created
Created --> Paid : payment received
Paid --> Shipped
Shipped --> Delivered
Delivered --> [*]
"""
),

"gantt": (
f"""
You are a Mermaid.js expert specialising in Gantt charts.

{_BASE_RULES}

Internal reasoning guide (DO NOT OUTPUT):
{_REASONING_GUIDE}

Rules:
· Start with 'gantt'
· Next line dateFormat YYYY-MM-DD
· Third line title

Few-shot Example

Correct Output:
gantt
dateFormat YYYY-MM-DD
title Project Timeline

section Development
Backend API :done, api1, 2026-01-01, 5d
Frontend UI :active, ui1, after api1, 7d
"""
),

"mindmap": (
f"""
You are a Mermaid.js expert specialising in mindmaps.

{_BASE_RULES}

Internal reasoning guide (DO NOT OUTPUT):
{_REASONING_GUIDE}

Rules:
· Start with 'mindmap'
· Hierarchy defined by indentation
· Do not mix shapes with icons

Few-shot Example

Correct Output:
mindmap
  Root
    Backend
      API
      Database
    Frontend
      UI
      State Management
"""
),

"custom": (
f"""
You are a Mermaid.js expert.

{_BASE_RULES}

Internal reasoning guide (DO NOT OUTPUT):
{_REASONING_GUIDE}

Choose the most appropriate diagram type for the request.

Valid diagram headers:
flowchart TD
sequenceDiagram
erDiagram
classDiagram
stateDiagram-v2
gantt
mindmap
"""
)
}


# ══════════════════════════════════════════════════════════════════════════════
# Per-type sanitisers
# ══════════════════════════════════════════════════════════════════════════════

def _sanitize_flowchart(text: str) -> str:
    # Normalise multi-dash arrows
    text = re.sub(r"-{3,}>", "-->", text)
    text = re.sub(r"==>", "-->", text)
    # Fix stray '>' after closing pipe: -->|label|>  →  -->|label|
    text = re.sub(r"\|([^|\n]*)\|>", r"|\1|", text)
    # Strip HTML tags inside node labels
    text = re.sub(r"</?(?:b|i|br|u|em|strong)[^>]*>", "", text, flags=re.IGNORECASE)

    def _clean_label(m: re.Match) -> str:
        label = m.group(1).replace("<", "").replace(">", "").replace("`", "").replace('"', "'")
        return f"|{label}|"

    text = re.sub(r"\|([^|\n]+)\|", _clean_label, text)

    # Fix unclosed square brackets per line
    fixed = []
    for line in text.splitlines():
        s = line.rstrip()
        diff = s.count("[") - s.count("]")
        if diff > 0:
            s += "]" * diff
        fixed.append(s)
    return "\n".join(fixed)


def _sanitize_sequence(text: str) -> str:
    # ->>> → ->>
    text = re.sub(r"->>{2,}", "->>", text)
    # ---> or -->> → -->>  (dotted response)
    text = re.sub(r"-{3,}>+", "-->>", text)
    # Bare --> (not part of ->>) → -->>
    text = re.sub(r"-->[^>]", lambda m: "-->>" + m.group(0)[-1], text)
    # Single -> that is NOT part of ->> → ->>
    text = re.sub(r"(?<![-\n\s])->(?!>)", "->>", text)
    return text


def _sanitize_erd(text: str) -> str:
    # Ensure every relationship line has a quoted label
    # Pattern: ENTITY rel ENTITY (no trailing "label")
    def _add_label(m: re.Match) -> str:
        line = m.group(0)
        if '"' not in line:
            line = line.rstrip() + ' : "relates to"'
        return line
    # Match relationship lines: word boundary + cardinality tokens + word boundary
    text = re.sub(
        r"^\s*\w[\w_]*\s+[|o}{]{2,}\s*-{2}\s*[|o}{]{2,}\s+\w[\w_]*\s*$",
        _add_label,
        text,
        flags=re.MULTILINE,
    )
    return text


def _sanitize_class(text: str) -> str:
    # Remove flowchart keywords that sometimes bleed in
    text = re.sub(r"^(flowchart|graph)\s+(TD|LR|TB|RL|BT)\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^subgraph\b", "namespace", text, flags=re.MULTILINE)

    # Balance curly braces per namespace block
    fixed = []
    for line in text.splitlines():
        s = line.rstrip()
        # Don't double-close lines that already close a block
        diff = s.count("{") - s.count("}")
        if diff > 0:
            s += "}" * diff
        fixed.append(s)
    return "\n".join(fixed)


def _sanitize_state(text: str) -> str:
    # Strip pipe-delimited edge labels — those belong to flowcharts
    text = re.sub(r"\|([^|\n]+)\|", "", text)
    # ->> or -->> are sequence arrows — replace with -->
    text = re.sub(r"--?>>", "-->", text)
    return text


def _sanitize_gantt(text: str) -> str:
    lines = text.splitlines()

    # Ensure dateFormat is the second non-empty, non-header line
    content_lines = [l for l in lines if l.strip() and not l.strip().startswith("gantt")]
    has_date_format = any(l.strip().startswith("dateFormat") for l in content_lines)
    has_title = any(l.strip().startswith("title") for l in content_lines)

    if not has_date_format:
        # Insert after 'gantt' header
        new_lines = []
        inserted = False
        for line in lines:
            new_lines.append(line)
            if line.strip().startswith("gantt") and not inserted:
                new_lines.append("    dateFormat YYYY-MM-DD")
                inserted = True
        lines = new_lines

    if not has_title:
        new_lines = []
        inserted = False
        for line in lines:
            new_lines.append(line)
            if line.strip().startswith("dateFormat") and not inserted:
                new_lines.append("    title Project Plan")
                inserted = True
        lines = new_lines

    # Fix invalid status tokens on task lines
    _INVALID_STATUS = re.compile(r"\b(completed|pending|todo|blocked|waiting|scheduled)\b", re.IGNORECASE)
    _STATUS_MAP = {
        "completed": "done",
        "pending":   "active",
        "todo":      "active",
        "blocked":   "crit",
        "waiting":   "active",
        "scheduled": "active",
    }
    fixed = []
    for line in lines:
        if re.search(r":", line) and not line.strip().startswith(("gantt", "dateFormat", "title", "section", "%%", "axisFormat", "excludes")):
            line = _INVALID_STATUS.sub(lambda m: _STATUS_MAP.get(m.group(0).lower(), "active"), line)
        fixed.append(line)

    return "\n".join(fixed)


def _sanitize_mindmap(text: str) -> str:
    lines = text.splitlines()
    fixed = []
    for line in lines:
        stripped = line.rstrip()

        # Remove shape modifier that follows ::icon(...)  e.g. "Label ::icon(...) (((root)))"
        stripped = re.sub(
            r"(::icon\([^)]*\))\s*[\(\[\{]+[^\)\]\}]*[\)\]\}]+",
            r"\1",
            stripped,
        )

        # Remove bare trailing shape token after a plain label (not a properly wrapped node)
        # e.g.  "System Features [branch]"  →  "System Features"
        # but leave  "[System Features]"  or  "((Root))"  intact (they start with the shape)
        indent = len(stripped) - len(stripped.lstrip())
        inner = stripped.lstrip()
        if inner and inner[0] not in ("(", "[", "{"):
            # It's a plain-text label — strip any dangling (word) or [word] at the end
            inner = re.sub(r"\s+[\(\[]\w[\w\s]*[\)\]]\s*$", "", inner)
            stripped = " " * indent + inner

        # Strip any HTML remnants
        stripped = re.sub(r"<[^>]+>", "", stripped)

        fixed.append(stripped)
    return "\n".join(fixed)


# ── Master sanitiser ───────────────────────────────────────────────────────────

def _sanitize_mermaid(text: str, diagram_type: str) -> str:
    text = text.strip()

    # 1. Strip markdown fences
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    text = text.strip()

    # 2. Remove %%{init: ...}%% directives
    text = re.sub(r"%%\{init.*?\}%%\s*\n?", "", text, flags=re.DOTALL)

    # 3. Apply per-type fixes BEFORE header injection
    _type_sanitizers = {
        "flowchart": _sanitize_flowchart,
        "sequence":  _sanitize_sequence,
        "erd":       _sanitize_erd,
        "class":     _sanitize_class,
        "state":     _sanitize_state,
        "gantt":     _sanitize_gantt,
        "mindmap":   _sanitize_mindmap,
        "custom":    _sanitize_flowchart,  # default to flowchart rules for custom
    }
    sanitizer = _type_sanitizers.get(diagram_type)
    if sanitizer:
        text = sanitizer(text)

    # 4. Ensure valid header
    expected_header = DIAGRAM_HEADERS.get(diagram_type, "flowchart TD")
    valid_starts = (
        "flowchart", "graph", "sequenceDiagram", "erDiagram",
        "classDiagram", "stateDiagram", "gantt", "mindmap",
    )
    lines = text.splitlines()
    if not lines or not any(lines[0].strip().startswith(h) for h in valid_starts):
        lines.insert(0, expected_header)
        text = "\n".join(lines)

    return text


# ══════════════════════════════════════════════════════════════════════════════
# Server-side syntax validator (per-type)
# ══════════════════════════════════════════════════════════════════════════════

def _verify_mermaid_syntax(code: str, diagram_type: str) -> Tuple[bool, str]:
    """
    Lightweight server-side check for obvious Mermaid syntax errors.
    Returns (is_valid, error_message).
    """
    code = code.strip()
    if not code:
        return False, "Empty diagram code returned by model"

    lines = [l for l in code.split("\n") if l.strip()]
    if not lines:
        return False, "Diagram code contains only whitespace"

    first = lines[0].strip()

    if first.startswith("```"):
        return False, "Model returned markdown fences — stripping failed"

    # ── Header check ──────────────────────────────────────────────────────────
    VALID_STARTS: dict[str, tuple] = {
        "flowchart": ("flowchart ", "flowchart\n", "graph "),
        "sequence":  ("sequenceDiagram",),
        "erd":       ("erDiagram",),
        "class":     ("classDiagram",),
        "state":     ("stateDiagram",),
        "gantt":     ("gantt",),
        "mindmap":   ("mindmap",),
        "custom":    ("flowchart", "graph", "sequenceDiagram", "erDiagram",
                      "classDiagram", "stateDiagram", "gantt", "mindmap"),
    }
    prefixes = VALID_STARTS.get(diagram_type, ())
    if prefixes and not any(first.startswith(p) for p in prefixes):
        return False, (
            f"Diagram header '{first}' is wrong for type '{diagram_type}'. "
            f"Expected one of: {list(prefixes)}"
        )

    # ── Sequence-specific ─────────────────────────────────────────────────────
    if diagram_type == "sequence":
        bad_triple = re.search(r"(->{3,})", code)
        if bad_triple:
            return False, f"Invalid arrow '{bad_triple.group(1)}'. Use '->>' (solid) or '-->>' (dotted)."
        if re.search(r"(?<![->])->(?!>)", code):
            return False, "Flowchart arrow '->' found in sequence diagram. Replace with '->>'."
        if re.search(r"(?<!>)-->(?!>)", code):
            return False, "Flowchart arrow '-->' found in sequence diagram. Replace with '-->>'."

    # ── Flowchart-specific ────────────────────────────────────────────────────
    if diagram_type in ("flowchart", "custom"):
        if re.search(r"->{3,}", code):
            return False, "Invalid '>>>' arrow. Use '-->' in flowcharts."
        if re.search(r"->>", code):
            return False, "Sequence arrow '->>' found in flowchart. Use '-->' instead."
        diff_sq = abs(code.count("[") - code.count("]"))
        if diff_sq > 4:
            return False, (
                f"Unbalanced square brackets: {code.count('[')}'[' vs {code.count(']')}']'"
            )

    # ── ERD-specific ──────────────────────────────────────────────────────────
    if diagram_type == "erd":
        rel_lines = [
            l.strip() for l in code.splitlines()
            if re.search(r"[|o}{]{2,}\s*-{2}\s*[|o}{]{2,}", l)
        ]
        for rel in rel_lines:
            if '"' not in rel:
                return False, (
                    f"ERD relationship line missing quoted label: '{rel}'. "
                    "Add : \"label\" at the end."
                )

    # ── Class-specific ────────────────────────────────────────────────────────
    if diagram_type == "class":
        if re.search(r"^(flowchart|graph)\s", code, re.MULTILINE):
            return False, "Flowchart header found inside class diagram."
        open_b = code.count("{")
        close_b = code.count("}")
        if abs(open_b - close_b) > 2:
            return False, f"Unbalanced curly braces: {open_b}'{{' vs {close_b}'}}'"

    # ── State-specific ────────────────────────────────────────────────────────
    if diagram_type == "state":
        if re.search(r"\|[^|\n]+\|", code):
            return False, "Pipe-delimited edge labels '|label|' are not valid in state diagrams."
        if re.search(r"--?>>", code):
            return False, "Sequence arrows '->>' / '-->>' are not valid in state diagrams."

    # ── Gantt-specific ────────────────────────────────────────────────────────
    if diagram_type == "gantt":
        if not re.search(r"^\s*dateFormat\b", code, re.MULTILINE):
            return False, "Gantt chart is missing required 'dateFormat' line."
        if not re.search(r"^\s*section\b", code, re.MULTILINE):
            return False, "Gantt chart is missing at least one 'section' block."
        invalid_status = re.search(
            r"\b(completed|pending|todo|blocked|waiting|scheduled)\b", code, re.IGNORECASE
        )
        if invalid_status:
            return False, (
                f"Invalid task status '{invalid_status.group(0)}'. "
                "Valid statuses: done, active, crit."
            )

    # ── Mindmap-specific ──────────────────────────────────────────────────────
    if diagram_type == "mindmap":
        # Detect icon + shape combination on same node
        if re.search(r"::icon\([^)]*\)\s*[\(\[{]{2,}", code):
            return False, (
                "Mindmap node combines ::icon() with a shape modifier on the same line. "
                "Use one or the other, not both."
            )
        # Detect bare trailing [word] on a plain-text label line
        bad_shape = re.search(r"^\s+\w[\w\s]+\s+\[\w+\]\s*$", code, re.MULTILINE)
        if bad_shape:
            return False, (
                f"Mindmap node has an invalid trailing shape token: '{bad_shape.group(0).strip()}'. "
                "Either wrap the entire label in [...] or remove the trailing [word]."
            )

    return True, ""


# ══════════════════════════════════════════════════════════════════════════════
# Path helpers
# ══════════════════════════════════════════════════════════════════════════════

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _svg_url(user_id: str, diagram_id: str, version_number: int) -> str:
    return f"{STATIC_URL_PREFIX}/{user_id}/{diagram_id}/v{version_number}.svg"


def _svg_disk_path(user_id: str, diagram_id: str, version_number: int) -> Path:
    directory = DIAGRAMS_DIR / user_id / diagram_id
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"v{version_number}.svg"


def _get_short_path(long_path: str) -> str:
    if platform.system() != "Windows":
        return long_path
    _GetShortPathNameW = ctypes.windll.kernel32.GetShortPathNameW
    _GetShortPathNameW.argtypes = [
        ctypes.wintypes.LPCWSTR, ctypes.wintypes.LPWSTR, ctypes.wintypes.DWORD,
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


# ══════════════════════════════════════════════════════════════════════════════
# SVG renderer
# ══════════════════════════════════════════════════════════════════════════════

def _render_svg(mermaid_code: str, disk_path: Path) -> None:
    disk_path.parent.mkdir(parents=True, exist_ok=True)
    mmd_path = disk_path.with_suffix(".mmd")

    with open(mmd_path, "w", encoding="utf-8") as f:
        f.write(mermaid_code)

    mmdc = _find_mmdc()
    cmd = [mmdc, "-i", str(mmd_path), "-o", str(disk_path)]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(f"diagram_service | SVG rendered | path={disk_path}")
        if result.stdout:
            logger.debug(f"diagram_service | mmdc stdout | {result.stdout}")
    except subprocess.CalledProcessError as e:
        logger.error(f"diagram_service | mmdc error | stderr={e.stderr}")
        raise HTTPException(
            status_code=500,
            detail=f"Diagram rendering failed: {e.stderr[:400]}",
        )


# ══════════════════════════════════════════════════════════════════════════════
# LLM call with server-side retry
# ══════════════════════════════════════════════════════════════════════════════

async def generate_mermaid_code(
    prompt: str,
    diagram_type: str,
    project_name: str,
    context_str: str = "",
    error_feedback: str = "",
    detail_level: str = "standard",
) -> str:
    system_prompt = SYSTEM_PROMPTS.get(diagram_type, SYSTEM_PROMPTS["custom"])
    detail_instruction = _DETAIL_INSTRUCTIONS.get(detail_level, _DETAIL_INSTRUCTIONS["standard"])
    model = os.environ.get("GROQ_DIAGRAM_MODEL", _DEFAULT_MODEL)

    last_feedback = error_feedback
    last_code = ""

    for attempt in range(SERVER_RETRY_LIMIT + 1):
        parts: list[str] = [
            f"Project: {project_name}",
            f"Diagram type: {diagram_type} ({DIAGRAM_LABELS.get(diagram_type, diagram_type)})",
            f"Detail level: {detail_level.upper()} — {detail_instruction}",
        ]

        if context_str:
            parts.append(context_str)

        parts.append(f"Requirement: {prompt}")

        if last_feedback:
            parts.append(
                f"\n⚠️  PREVIOUS ATTEMPT FAILED with this error — fix it:\n"
                f"{last_feedback}\n"
                f"Return ONLY the corrected Mermaid code."
            )

        parts.append("\nGenerate the Mermaid diagram code now.")
        user_message = "\n".join(parts)

        try:
            response = await litellm.acompletion(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_message},
                ],
                temperature=0.15,
                max_tokens=3000,
            )
            raw = response.choices[0].message.content or ""
            logger.debug(f"diagram_service | attempt={attempt+1} | raw={raw[:120]}")
        except Exception as e:
            logger.error(f"diagram_service | LLM error | attempt={attempt+1} | {e}")
            if attempt >= SERVER_RETRY_LIMIT:
                raise HTTPException(status_code=500, detail=f"LLM generation failed: {e}")
            last_feedback = f"LLM call failed: {e}. Try a simpler diagram."
            continue

        sanitized = _sanitize_mermaid(raw, diagram_type)
        last_code = sanitized

        is_valid, err = _verify_mermaid_syntax(sanitized, diagram_type)
        if is_valid:
            if attempt > 0:
                logger.info(f"diagram_service | syntax OK after {attempt+1} attempts")
            return sanitized

        logger.warning(f"diagram_service | validation failed attempt={attempt+1} | {err}")
        last_feedback = err

    logger.error("diagram_service | server retries exhausted, returning last code")
    return last_code or _fallback_diagram(diagram_type, prompt)


def _fallback_diagram(diagram_type: str, prompt: str) -> str:
    """Return a minimal valid diagram when all retries fail."""
    if diagram_type == "sequence":
        return (
            "sequenceDiagram\n"
            "    participant User\n"
            "    participant System\n"
            f"    User->>System: {prompt[:60]}\n"
            "    System-->>User: Response"
        )
    if diagram_type == "gantt":
        return (
            "gantt\n"
            "    dateFormat YYYY-MM-DD\n"
            "    title Project Plan\n"
            "    section Phase 1\n"
            "    Task :a1, 2025-01-01, 30d"
        )
    if diagram_type == "erd":
        return (
            'erDiagram\n'
            '    ENTITY1 ||--|| ENTITY2 : "relates to"\n'
            '    ENTITY1 {\n'
            '        int id PK\n'
            '        string name\n'
            '    }'
        )
    if diagram_type == "mindmap":
        return (
            "mindmap\n"
            f"  root(({prompt[:40]}))\n"
            "    Topic1\n"
            "    Topic2\n"
            "    Topic3"
        )
    header = DIAGRAM_HEADERS.get(diagram_type, "flowchart TD")
    return f"{header}\n    A[{prompt[:40]}] --> B[Result]"


# ══════════════════════════════════════════════════════════════════════════════
# Public service functions
# ══════════════════════════════════════════════════════════════════════════════

async def create_diagram(
    db: Any,
    user_id: str,
    project_name: str,
    prompt: str,
    diagram_type: str,
    context_str: str = "",
    error_feedback: str = "",
    detail_level: str = "standard",
) -> DiagramOut:
    mermaid_code = await generate_mermaid_code(
        prompt=prompt,
        diagram_type=diagram_type,
        project_name=project_name,
        context_str=context_str,
        error_feedback=error_feedback,
        detail_level=detail_level,
    )

    repo = DiagramRepo(db)
    temp_diagram_id = str(uuid.uuid4())
    disk_path = _svg_disk_path(user_id, temp_diagram_id, 1)
    _render_svg(mermaid_code, disk_path)

    temp_svg_url = _svg_url(user_id, temp_diagram_id, 1)
    diagram_id = await repo.create_diagram(
        user_id=user_id,
        project_name=project_name,
        diagram_type=diagram_type,
        prompt=prompt,
        mermaid_code=mermaid_code,
        svg_path=temp_svg_url,
    )

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
    detail_level: str = "standard",
) -> DiagramOut:
    repo = DiagramRepo(db)
    existing = await repo.get_diagram(user_id, diagram_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Diagram not found")

    mermaid_code = await generate_mermaid_code(
        prompt=prompt,
        diagram_type=diagram_type,
        project_name=existing["project_name"],
        context_str=context_str,
        error_feedback=error_feedback,
        detail_level=detail_level,
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
    repo = DiagramRepo(db)
    existing = await repo.get_diagram(user_id, diagram_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Diagram not found")

    diagram_type = existing.get("diagram_type", "custom")
    clean_code = _sanitize_mermaid(mermaid_code, diagram_type)

    is_valid, err = _verify_mermaid_syntax(clean_code, diagram_type)
    if not is_valid:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid Mermaid syntax: {err}. Please fix the code and try again.",
        )

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