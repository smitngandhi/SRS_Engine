# Diagram Creation Feature — Implementation Plan

## Overview

Add a full **Diagram Studio** to SRS_Engine that lets users generate, preview, edit, version, and store Mermaid diagrams tied to their projects — all powered by the existing Groq LLM backend. The feature uses the same architectural patterns already established in the codebase (MongoDB repos, Pydantic schemas, FastAPI routers, Jinja2 templates, vanilla CSS/JS).

---

## Proposed Changes

### 1. Database Layer

#### [NEW] `diagram_repo.py` — `srs_engine/core/db/diagram_repo.py`
A new MongoDB repository (same pattern as [job_repo.py](file:///c:/srs%20engine/SRS_Engine/srs_engine/core/db/job_repo.py) and [user_repo.py](file:///c:/srs%20engine/SRS_Engine/srs_engine/core/db/user_repo.py)):
- `create_diagram(user_id, project_name, prompt, mermaid_code, diagram_type, svg_path)` → returns `diagram_id` (UUID)
- `create_version(diagram_id, prompt, mermaid_code, svg_path)` → appends version, increments version number
- `get_diagram(user_id, diagram_id)` → single diagram with all versions
- `list_by_project(user_id, project_name)` → all diagrams for a project
- `list_recent(user_id, limit=6)` → recent diagrams for home page dashboard
- `delete_diagram(user_id, diagram_id)` → soft delete

MongoDB collection: `diagrams`
Document structure:
```
{
  diagram_id: UUID string,
  user_id: str,
  project_name: str,
  diagram_type: str,        # "flowchart" | "sequence" | "erd" | "class" | "custom"
  created_at: datetime,
  updated_at: datetime,
  versions: [
    {
      version_id: UUID,
      version_number: int,
      prompt: str,
      mermaid_code: str,
      svg_path: str,        # srs_engine/static/diagrams/{user_id}/{diagram_id}/v{n}.svg
      created_at: datetime
    }
  ]
}
```

#### [MODIFY] [mongo.py](file:///c:/srs%20engine/SRS_Engine/test_mongo.py) — [srs_engine/core/db/mongo.py](file:///c:/srs%20engine/SRS_Engine/srs_engine/core/db/mongo.py)
Add index declarations for the `diagrams` collection inside [init_mongo()](file:///c:/srs%20engine/SRS_Engine/srs_engine/core/db/mongo.py#22-55):
```python
await db.diagrams.create_index("diagram_id", unique=True)
await db.diagrams.create_index([("user_id", ASCENDING), ("updated_at", DESCENDING)])
await db.diagrams.create_index([("user_id", ASCENDING), ("project_name", ASCENDING)])
```

---

### 2. Pydantic Schemas

#### [NEW] `diagram_schemas.py` — `srs_engine/schemas/diagram_schemas/diagram_schemas.py`
```python
class DiagramGenerateRequest(BaseModel):
    project_name: str
    prompt: str
    diagram_type: str = "flowchart"  # flowchart | sequence | erd | class | custom

class DiagramRegenerateRequest(BaseModel):
    diagram_id: str
    prompt: str
    diagram_type: str

class DiagramEditRequest(BaseModel):
    diagram_id: str
    mermaid_code: str   # user edited the Mermaid code directly

class DiagramVersionResponse(BaseModel):
    version_id: str
    version_number: int
    prompt: str
    mermaid_code: str
    svg_path: str
    created_at: datetime

class DiagramResponse(BaseModel):
    diagram_id: str
    project_name: str
    diagram_type: str
    created_at: datetime
    updated_at: datetime
    versions: list[DiagramVersionResponse]
    current_version: DiagramVersionResponse  # latest version
```

---

### 3. Backend Service

#### [NEW] `diagram_service.py` — `srs_engine/core/services/diagram_service.py`
Core service functions:

**`generate_mermaid_code(prompt, diagram_type, project_name)`**  
Calls Groq LLM (via the existing `litellm`/`groq` setup) with a structured system prompt:
- System prompt instructs the model to output **only valid raw Mermaid syntax** (no markdown fences, no extra text)
- Includes diagram-type-specific guidance (e.g., for `sequence`, use `sequenceDiagram`; for `erd`, use `erDiagram`)
- Returns the cleaned Mermaid code string

**`render_svg(mermaid_code, output_path)`**  
Uses `mmdc` (already installed for SRS generation) to render the Mermaid code to SVG:
```python
subprocess.run([MMDC_PATH, "-i", str(mmd_path), "-o", str(output_path), "-e", "svg"], check=True)
```
Output path: `srs_engine/static/diagrams/{user_id}/{diagram_id}/v{n}.svg`

**`create_diagram(user_id, request_data)`**  
Full pipeline: generate_mermaid_code → render_svg → diagram_repo.create_diagram → return DiagramResponse

**`regenerate_diagram(user_id, request_data)`**  
Same as create, but calls `diagram_repo.create_version` instead (adds new version to existing diagram)

**`save_edited_diagram(user_id, request_data)`**  
Skips LLM; directly renders user-supplied mermaid_code → render_svg → `diagram_repo.create_version`

**`get_diagram(user_id, diagram_id)`**  
Loads from MongoDB, returns DiagramResponse

**`list_diagrams_by_project(user_id, project_name)`**  
Returns list of DiagramResponse for a project

**`list_recent_diagrams(user_id)`**  
Returns 6 most recently updated diagrams for home page widget

---

### 4. Router

#### [NEW] `diagram_router.py` — `srs_engine/core/routers/diagram_router.py`

| Method | Path | Description |
|---|---|---|
| `GET` | `/diagrams` | Render the Diagram Studio page |
| `POST` | `/api/diagrams/generate` | Generate new diagram → returns `DiagramResponse` |
| `POST` | `/api/diagrams/{diagram_id}/regenerate` | Add new version from new prompt |
| `PATCH` | `/api/diagrams/{diagram_id}/edit` | Save manually edited Mermaid code as new version |
| `GET` | `/api/diagrams/{diagram_id}` | Load a specific diagram (all versions) |
| `GET` | `/api/diagrams/project/{project_name}` | All diagrams for a project |
| `GET` | `/api/diagrams/recent` | Last 6 diagrams for home dashboard |
| `DELETE` | `/api/diagrams/{diagram_id}` | Soft-delete a diagram |

All routes require `user=Depends(require_user)`.

#### [MODIFY] [__init__.py](file:///c:/srs%20engine/SRS_Engine/srs_engine/__init__.py) — [srs_engine/core/routers/__init__.py](file:///c:/srs%20engine/SRS_Engine/srs_engine/core/routers/__init__.py)
Import and export `diagram_router`.

#### [MODIFY] [main.py](file:///c:/srs%20engine/SRS_Engine/srs_engine/main.py) — [srs_engine/main.py](file:///c:/srs%20engine/SRS_Engine/srs_engine/main.py)
Register `diagram_router` in [create_app()](file:///c:/srs%20engine/SRS_Engine/srs_engine/main.py#59-90).

---

### 5. Templates

#### [NEW] `diagram_studio.html` — `srs_engine/templates/pages/diagram_studio.html`
Full-featured single-page diagram studio:
- **Left panel**: 
  - Project selector dropdown (populated from user's existing SRS projects)
  - Diagram type selector (Flowchart / Sequence / ER Diagram / Class / Custom)
  - Prompt textarea with example hints per diagram type
  - Generate button + Regenerate button
- **Center panel**:
  - Live SVG preview area (renders the SVG inline)
  - Loading spinner during generation
- **Right panel**:
  - Mermaid code editor (`<textarea>` with monospace font)
  - "Apply Edit" button to save manually edited code as new version
  - Version history accordion (list of versions, click to load any)
- **Bottom bar**:
  - "All Diagrams for this Project" link
  - Download SVG button

#### [MODIFY] [landing.html](file:///c:/srs%20engine/SRS_Engine/srs_engine/templates/pages/landing.html) — [srs_engine/templates/pages/landing.html](file:///c:/srs%20engine/SRS_Engine/srs_engine/templates/pages/landing.html)
Add a **"My Diagrams"** section (after "My Generated SRS", before the SRS Upgrader banner):
```html
{% if user %}
<section id="my-diagrams" class="documents-section">
  <div class="reveal">
    <span class="section-label">Visual workspace</span>
    <h2 class="section-heading">My Diagrams</h2>
    <p class="section-sub">Recently generated Mermaid diagrams — grouped by project.</p>
  </div>
  <div id="diagramsGrid" class="docs-grid"><!-- JS populated --></div>
  <a class="btn btn-secondary" href="/diagrams">Open Diagram Studio →</a>
</section>
<hr class="section-divider">
{% endif %}
```

#### [MODIFY] [base.html](file:///c:/srs%20engine/SRS_Engine/srs_engine/templates/base.html) — [srs_engine/templates/base.html](file:///c:/srs%20engine/SRS_Engine/srs_engine/templates/base.html)
Add `Diagrams` nav link:
```html
<a href="/diagrams">Diagrams</a>
```

---

### 6. Static Assets

#### [NEW] `diagram_studio.css` — `srs_engine/static/diagram_studio.css`
Three-panel layout using CSS grid. Design system consistent with existing [site.css](file:///c:/srs%20engine/SRS_Engine/srs_engine/static/site.css) / [upgrader_review.css](file:///c:/srs%20engine/SRS_Engine/srs_engine/static/upgrader_review.css) — dark theme, glassmorphism panels, gradient accents.

#### [NEW] `diagram_studio.js` — `srs_engine/static/diagram_studio.js`
Client-side logic:
- On load: fetch `/api/diagrams/recent` to populate project dropdown and recent grid
- `generateDiagram()`: POST to `/api/diagrams/generate`, receive SVG path, render inline
- `regenerateDiagram()`: POST to `/api/diagrams/{id}/regenerate`
- `applyEdit()`: PATCH to `/api/diagrams/{id}/edit` with textarea content
- `loadVersion(versionId)`: swap SVG preview + populate code editor with historical version
- `downloadSVG()`: fetch the SVG file and trigger browser download
- Mermaid.js loaded from CDN for **client-side live preview** of the code editor (renders in real-time as user types, separate from the server-rendered version)

#### [MODIFY] [site.js](file:///c:/srs%20engine/SRS_Engine/srs_engine/static/site.js) — [srs_engine/static/site.js](file:///c:/srs%20engine/SRS_Engine/srs_engine/static/site.js)
Add `loadDiagrams()` function (mirrors `loadDocuments()`) to populate the home page "My Diagrams" widget via `/api/diagrams/recent`.

---

## Verification Plan

### Manual Verification Steps

> Start the server with: `uvicorn srs_engine.main:app --reload` from `c:\srs engine\SRS_Engine`

1. **Nav link** — Visit `http://127.0.0.1:8000/home`. Confirm "Diagrams" appears in the top nav bar.

2. **Home widget** — Log in. On the home page, scroll to "My Diagrams" section. Initially shows empty state. After generating a diagram it should show the card.

3. **Diagram page loads** — Navigate to `http://127.0.0.1:8000/diagrams`. Page should load the three-panel studio UI without errors.

4. **Generate flowchart** — Select a project, choose "Flowchart", enter prompt `"User login and registration flow"`, click Generate. Preview panel should show the rendered SVG. Right panel should show the Mermaid code.

5. **Edit & apply** — Modify one line in the Mermaid code editor. Click "Apply Edit". A new version should appear in the version history. The preview should update.

6. **Regenerate** — Change the prompt to `"Add password reset flow"`. Click Regenerate. A second version should appear alongside v1 in the version history accordion.

7. **Version history** — Click v1 in the version history. The preview and code editor should revert to the v1 content.

8. **Download SVG** — Click Download SVG. Browser should download `{project}_{diagram_id}_v2.svg`.

9. **Project filter** — Generate a second diagram for a different project. Return to `/diagrams`. Both diagrams should be accessible without mixing each other's versions.

10. **Home dashboard** — Return to `/home`. "My Diagrams" section should now show the recent diagrams as cards.
