# SRS Generated Upgrader — Technical Plan v2.1

## Overview

A new upgrader pipeline **exclusively for SRS documents generated on this platform.**
Completely separate from the existing external-file upgrader (upload PDF/DOCX → parse → Q&A pipeline).
That pipeline stays 100% untouched.

---

## What Stays Untouched

- `upgrade_router.py` — external file upgrader routes
- `upgrade_service.py` — parse / analyse / Q&A pipeline
- `section_analyzer_agent`, `question_engine` — existing agents
- All existing frontend pages

---

## Architecture

```
Generation (existing)          New storage after generation
──────────────────────         ──────────────────────────────────────
srs_service.generate_srs()
  └── generates .docx ──────── generated_srs/{user_id}/{project}_SRS.docx
  └── NEW: saves JSON ───────── generated_srs/{user_id}/{project}_sections.json
  └── NEW: saves meta ───────── generated_srs/{user_id}/{project}_meta.json
  └── NEW: builds FAISS ─────── generated_srs/{user_id}/{project}_rag.faiss
  └── NEW: saves key map ─────── generated_srs/{user_id}/{project}_rag_map.npy
```

---

## 1. Storage Changes — `srs_service.py`

After `generate_srs_document()` succeeds, call:
- `_save_generated_srs_json()`
- `_build_rag_index()`

### `{project}_sections.json`
```json
{
  "domain": "technical",
  "project_name": "HireSmart",
  "introduction_section": { "...": "..." },
  "overall_description_section": { "...": "..." },
  "system_features_section": { "...": "..." },
  "external_interfaces_section": { "...": "..." },
  "nfr_section": { "...": "..." },
  "glossary_section": { "...": "..." },
  "assumptions_section": { "...": "..." }
}
```

### `{project}_meta.json` *(v2.1: added `modified_sections` for UI tracking and rollback support)*
```json
{
  "project_name": "HireSmart",
  "domain": "technical",
  "authors": ["John Doe"],
  "organization": "Acme Corp",
  "generated_at": "2026-03-31T10:00:00Z",
  "docx_path": "generated_srs/{user_id}/HireSmart_SRS.docx",
  "modified_sections": [],
  "section_keys": [
    "introduction_section",
    "overall_description_section",
    "system_features_section",
    "external_interfaces_section",
    "nfr_section",
    "glossary_section",
    "assumptions_section"
  ]
}
```

---

## 2. PageIndex Map — `utils/page_index_map.py`

Domain-aware registry. Every entry carries `section_type` to drive post-processing.

*(v2.1: indices spaced by 10 to prevent collisions when new sections are inserted between existing ones)*

```python
PAGE_INDEX_MAP: dict[str, list[dict]] = {
    "technical": [
        { "page_index": 10, "section_key": "introduction_section",          "section_type": "text",    "schema_module": "introduction_schema" },
        { "page_index": 20, "section_key": "overall_description_section",   "section_type": "text",    "schema_module": "overall_description_schema" },
        { "page_index": 30, "section_key": "system_features_section",       "section_type": "text",    "schema_module": "system_features_schema" },
        { "page_index": 40, "section_key": "external_interfaces_section",   "section_type": "diagram", "schema_module": "external_interfaces_schema" },
        { "page_index": 50, "section_key": "nfr_section",                   "section_type": "text",    "schema_module": "nfr_schema" },
        { "page_index": 60, "section_key": "glossary_section",              "section_type": "text",    "schema_module": "glossary_schema" },
        { "page_index": 70, "section_key": "assumptions_section",           "section_type": "text",    "schema_module": "assumptions_schema" },
    ],
    # Add "aerospace", "automotive", "healthcare" etc here — everything adapts automatically
}

def get_section_by_index(domain: str, page_index: int) -> dict | None:
    return next(
        (s for s in PAGE_INDEX_MAP.get(domain, []) if s["page_index"] == page_index),
        None
    )

def get_section_by_key(domain: str, section_key: str) -> dict | None:
    return next(
        (s for s in PAGE_INDEX_MAP.get(domain, []) if s["section_key"] == section_key),
        None
    )
```

---

## 3. FAISS RAG Index — `utils/srs_rag_index.py`

Model: `all-MiniLM-L6-v2` — 384-dimensional, ~22MB on disk, CPU-only.

*(v2.1: added in-memory index + map cache, better embedding text, safe path construction, cosine similarity)*

```python
from sentence_transformers import SentenceTransformer
import faiss, numpy as np, json
from pathlib import Path

_MODEL       = None   # lazy-loaded singleton
_INDEX_CACHE = {}     # v2.1: avoids disk reload per query
_MAP_CACHE   = {}

def _get_model() -> SentenceTransformer:
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer('all-MiniLM-L6-v2')
    return _MODEL
```

### Build (called after generation save)

```python
def _build_embedding_text(section_key: str, section_json: dict) -> str:
    # v2.1: embed a readable summary instead of a raw JSON dump
    title   = section_key.replace("_", " ")
    summary = json.dumps(section_json)[:300]
    return f"{title}: {summary}"

def build_rag_index(sections_json: dict, user_id: str, project_name: str) -> None:
    model   = _get_model()
    entries = []

    for key, section in sections_json.items():
        if isinstance(section, dict):
            entries.append({"key": key, "text": _build_embedding_text(key, section)})

    if not entries:
        return

    embeddings = model.encode([e["text"] for e in entries]).astype("float32")

    # v2.1: IndexFlatIP (cosine similarity) instead of IndexFlatL2
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    # v2.1: safe path construction via pathlib
    base_dir   = Path(f"./generated_srs/{user_id}")
    faiss_path = base_dir / f"{project_name}_rag.faiss"
    map_path   = base_dir / f"{project_name}_rag_map.npy"

    faiss.write_index(index, str(faiss_path))
    np.save(map_path, np.array([e["key"] for e in entries]))
```

### Search (called on pageIndex miss)

```python
def _load_index(user_id: str, project_name: str):
    # v2.1: cache to avoid disk I/O on every query
    cache_key = f"{user_id}:{project_name}"
    if cache_key in _INDEX_CACHE:
        return _INDEX_CACHE[cache_key], _MAP_CACHE[cache_key]

    base  = Path(f"./generated_srs/{user_id}")
    index = faiss.read_index(str(base / f"{project_name}_rag.faiss"))
    keys  = np.load(base / f"{project_name}_rag_map.npy", allow_pickle=True)

    _INDEX_CACHE[cache_key] = index
    _MAP_CACHE[cache_key]   = keys
    return index, keys

def search_section(
    query: str,
    user_id: str,
    project_name: str,
    top_k: int = 1,
) -> tuple[str, float]:
    """Returns (section_key, confidence_0_to_1)."""
    model              = _get_model()
    index, keys        = _load_index(user_id, project_name)
    query_vec          = model.encode([query]).astype("float32")
    distances, indices = index.search(query_vec, k=top_k)

    matched_key = keys[indices[0][0]]
    confidence  = float(1 / (1 + distances[0][0]))
    return matched_key, confidence
```

---

## 4. Section Types

| Type | pageIndex | Agent handles | Post-process after confirm |
|------|-----------|--------------|---------------------------|
| `text` | 10, 20, 30, 50, 60, 70 | Updates JSON fields | Save to `_sections.json` |
| `diagram` | 40 | Updates mermaid code strings inside JSON | Save JSON + re-render 4 PNGs via `render_mermaid_png()` |

**The single upgrade agent is identical for both types.** It only works with JSON.
The service layer handles the `section_type`-specific post-processing.

---

## 5. Single Upgrade Agent

### Location
```
agents/upgrader_agents/section_upgrade_agent/
  __init__.py
  agent.py    ← create_section_upgrade_agent()
  prompt.py   ← build_upgrade_prompt(...)
```

### Input payload to agent
```python
{
    "section_key": "external_interfaces_section",
    "section_type": "diagram",            # tells agent mermaid code strings are editable
    "user_instruction": "Add Redis cache between FastAPI and MongoDB",
    "current_section_json": { "...": "..." },   # full current section data
    "schema_description": "...",                # human-readable schema field descriptions
}
```

### Agent output (validated against section schema)
```python
{
    "upgraded_section_json": { "...": "..." },
    "changes_summary": "Added Redis cache node between FastAPI and MongoDB. Updated software_interfaces diagram code.",
    "fields_modified": ["software_interfaces.interface_diagram.code"],
}
```

### Key design principles

- The agent receives `section_type` so it understands when a string field contains mermaid graph code.
- The prompt instructs it to produce valid mermaid syntax and to only modify the `code` field inside `interface_diagram` objects — never touch PNG paths or image references.
- *(v2.1)* After the agent responds, `upgraded_json` is validated against the section schema before proceeding. If validation fails, the upgrade is rejected.

```python
from jsonschema import validate

# called in preview_upgrade() after agent response
validate(instance=upgraded_json, schema=section_schema)
```

---

## 6. Service — `generated_srs_upgrade_service.py`

```python
@dataclass
class SectionResult:
    page_index: int
    section_key: str
    section_type: str          # "text" | "diagram"
    section_data: dict
    lookup_method: str         # "pageindex" | "rag_fallback"
    rag_confidence: float | None = None

async def list_generated_srs(user_id: str) -> list[dict]:
    """Scan generated_srs/{user_id}/ for *_meta.json files. Returns list of meta dicts."""

async def get_section_by_pageindex(
    user_id: str, project_name: str, page_index: int
) -> SectionResult:
    """
    Fast path.
    1. Look up page_index in PAGE_INDEX_MAP[domain]
    2. If found: load section from _sections.json → return with lookup_method="pageindex"
    3. If not found: raise PageIndexError → caller falls back to /search
    """

async def search_section_rag(
    user_id: str, project_name: str, query: str
) -> SectionResult:
    """
    RAG fallback.
    1. Call search_section(query) via FAISS → matched_key, confidence
    2. Find page_index for matched_key via get_section_by_key()
    3. Load section data → return with lookup_method="rag_fallback"
    """

async def preview_upgrade(
    user_id: str,
    project_name: str,
    page_index: int,
    instruction: str,
    lookup_method: str,
) -> dict:
    """
    1. Load section + load schema description
    2. Call upgrade agent
    3. (v2.1) Validate upgraded_json against section schema — reject if invalid
    4. If diagram: validate mermaid syntax via render_mermaid_png(temp_code) — reject if render fails
    5. Return { original_json, upgraded_json, changes_summary, fields_modified }
    """

async def confirm_upgrade(
    user_id: str,
    project_name: str,
    page_index: int,
    upgraded_json: dict,
) -> None:
    """
    1. (v2.1) Back up current _sections.json → _sections_v{n}.json before writing
    2. Load _sections.json, replace [section_key] with upgraded_json
    3. If diagram section: re-render 4 PNGs via render_mermaid_png() to generated_images/
    4. Save _sections.json
    5. (v2.1) Append section_key to meta.modified_sections and save meta
    """

async def rebuild_docx(user_id: str, project_name: str) -> str:
    """
    Load all 7 sections from _sections.json (mix of original + confirmed upgrades).
    Call generate_srs_document() → new .docx.
    Returns path to new .docx.
    """
```

### v2.1 — Version Backup

Before every `confirm_upgrade` write, the current `_sections.json` is copied to a versioned file:

```
generated_srs/{user_id}/HireSmart_sections_v1.json
generated_srs/{user_id}/HireSmart_sections_v2.json
...
```

This enables full rollback to any previous state.

---

## 7. Router — `generated_srs_upgrade_router.py`

```
GET  /upgrade/generated/list
     → list_generated_srs(user_id)

GET  /upgrade/generated/{project}/section/{page_index}
     → get_section_by_pageindex() — fast path
     → 404 if page_index out of range for domain

POST /upgrade/generated/{project}/search
     body: { "query": str }
     → search_section_rag() — RAG fallback
     → returns: { section_result, page_index, confidence }

POST /upgrade/generated/{project}/section/{page_index}/preview
     body: { "instruction": str, "lookup_method": str }
     → preview_upgrade()
     → returns: { original_json, upgraded_json, changes_summary }

POST /upgrade/generated/{project}/section/{page_index}/confirm
     body: { "upgraded_json": dict }
     → confirm_upgrade()

POST /upgrade/generated/{project}/rebuild
     → rebuild_docx()
     → returns: { docx_path, download_url }
```

---

## 8. Frontend Pages

### Page 1 — `srs_generated_upgrader.html`
- SRS doc picker: cards for each generated doc (name, domain, date, modified count)
- Static files: `generated_upgrader.js`, `generated_upgrader.css`

### Page 2 — `srs_section_upgrader.html`
- Left sidebar (256px): section navigator (7 pills, type badges, modified indicators)
- Top bar: section name + type badge (TEXT / DIAGRAM) + lookup badge (PageIndex ✓ / RAG Fallback)
- Content area: rendered section content
  - Text sections: formatted field/value pairs grouped by subsection
  - Diagram sections: live mermaid.js SVG render from code strings
- Bottom: instruction textarea + "Preview Upgrade" button
- Preview overlay: side-by-side diff
  - Text: field-by-field with change highlights + NEW badges
  - Diagram: rendered SVGs side by side, "Modified" badge on changed diagrams
- Confirm / Discard / Rebuild Document buttons
- Static files: `section_upgrader.js`, `generated_upgrader.css`

---

## 9. Complete File Plan

| Action | File | Notes |
|--------|------|-------|
| **Modify** | `core/services/srs_service.py` | Add `_save_generated_srs_json()` + `_build_rag_index()` after docx save. |
| **New** | `utils/page_index_map.py` | Domain-aware map. `section_type` drives post-processing. Indices spaced by 10. |
| **New** | `utils/srs_rag_index.py` | FAISS + sentence-transformers. Build + cached search. Cosine similarity. |
| **New** | `agents/upgrader_agents/section_upgrade_agent/__init__.py` | |
| **New** | `agents/upgrader_agents/section_upgrade_agent/agent.py` | `create_section_upgrade_agent()` — single ADK agent, schema-aware. |
| **New** | `agents/upgrader_agents/section_upgrade_agent/prompt.py` | `build_upgrade_prompt()` — handles both text + diagram section types. |
| **New** | `core/services/generated_srs_upgrade_service.py` | All business logic. Versioned backups, meta tracking, mermaid + schema validation. |
| **New** | `core/routers/generated_srs_upgrade_router.py` | Routes only. Auth via `require_user`. |
| **New** | `templates/pages/srs_generated_upgrader.html` | SRS picker page. |
| **New** | `templates/pages/srs_section_upgrader.html` | Section upgrader page. |
| **New** | `static/generated_upgrader.js` | Picker page JS. |
| **New** | `static/section_upgrader.js` | Upgrader JS — pageIndex, RAG, preview, diff, mermaid render. |
| **New** | `static/generated_upgrader.css` | Shared CSS for both new pages. |

---

## 10. End-to-End Flow

```
── Generation ────────────────────────────────────────────────────────
generate_srs() completes
  ├── .docx saved (existing)
  ├── NEW: _sections.json saved  (all 7 section JSONs)
  ├── NEW: _meta.json saved      (project name, domain, authors, paths, modified_sections=[])
  └── NEW: FAISS index built     (_rag.faiss + _rag_map.npy)

── Normal Upgrade (PageIndex) ────────────────────────────────────────
User opens /srs-generated-upgrader
  └── GET /upgrade/generated/list → SRS doc cards

User clicks "HireSmart" → /srs-section-upgrader?project=HireSmart
  └── Sidebar loads 7 section pills

User clicks pill for External Interfaces (page_index=40)
  └── GET /upgrade/generated/HireSmart/section/40
  └── PageIndex map → external_interfaces_section ✓ (lookup_method="pageindex")
  └── Frontend renders 4 mermaid SVGs from code strings

User types: "Add Redis cache between FastAPI and MongoDB"
  └── POST /upgrade/generated/HireSmart/section/40/preview
  └── Agent receives: current_json + instruction + schema + section_type=diagram
  └── Agent returns: upgraded_json with new mermaid code strings
  └── Service validates JSON schema + mermaid render
  └── Response: { original_json, upgraded_json, changes_summary }

UI shows side-by-side: original SVG | upgraded SVG with "Modified" badge

User clicks Confirm
  └── POST /upgrade/generated/HireSmart/section/40/confirm
  └── _sections.json backed up → _sections_v1.json
  └── _sections.json updated for external_interfaces_section
  └── 4 PNGs re-rendered to generated_images/HireSmart/
  └── meta.modified_sections updated
  └── Sidebar pill shows ✓ Modified indicator

── RAG Fallback ──────────────────────────────────────────────────────
PageIndex lookup returns None (page_index out of range, or future domain mismatch)
  └── POST /upgrade/generated/HireSmart/search { "query": "improve performance requirements" }
  └── FAISS search: encode query → cosine search → top-1 match: "nfr_section" (confidence: 0.87)
  └── Service finds page_index=50 for nfr_section
  └── Returns: { section_data, page_index: 50, lookup_method: "rag_fallback", confidence: 0.87 }
  └── UI shows RAG Fallback badge + loads section

Rest of flow is identical to the normal path.

── Rebuild ───────────────────────────────────────────────────────────
User clicks "Rebuild Document"
  └── POST /upgrade/generated/HireSmart/rebuild
  └── Loads all 7 sections from _sections.json (mix of original + confirmed upgrades)
  └── Calls generate_srs_document() with updated sections
  └── New .docx saved
  └── Returns download URL
```

---

## 11. Dependency Additions

```txt
# requirements.txt additions
faiss-cpu>=1.7.4
sentence-transformers>=2.7.0
jsonschema>=4.21.0
```

No external DB, no server process — FAISS index is a flat file alongside the SRS doc.
Model is lazy-loaded once per worker process (~22MB RAM after first load).

---

## Changelog

### v2.1 (2026-03-31)

| Change | Details |
|--------|---------|
| **Stable PageIndex spacing** | Indices now use multiples of 10 (10–70) — prevents collisions when new sections are added |
| **FAISS in-memory cache** | `_INDEX_CACHE` / `_MAP_CACHE` dicts prevent disk reload on every RAG query |
| **Better embedding text** | `_build_embedding_text()` embeds a readable summary (300 chars) instead of a raw 400-char JSON dump |
| **Cosine similarity** | `IndexFlatIP` replaces `IndexFlatL2` for more accurate semantic retrieval |
| **Safe file paths** | All FAISS paths now use `pathlib.Path` construction |
| **JSON schema validation** | `upgraded_json` validated against section schema after agent response — rejects corrupt output |
| **Mermaid render validation** | `render_mermaid_png(temp_code)` called before confirming diagram upgrades — rejects broken diagrams |
| **Section version history** | `_sections.json` backed up to `_sections_v{n}.json` before every confirmed write — enables rollback |
| **`modified_sections` in meta** | `meta.modified_sections` appended on each confirmed upgrade — drives UI tracking and doc-level status |
| **`_build_rag_index()` split out** | `srs_service.py` now calls `_save_generated_srs_json()` and `_build_rag_index()` as separate steps |