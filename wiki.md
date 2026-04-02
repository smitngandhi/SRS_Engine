# 📜 SRS Engine - Technical Wiki

This document explains the end-to-end architecture, file structure, and step-by-step processes of the SRS Engine Plan Upgrader.

---

## 🏗️ 1. High-Level Architecture

The application follows an **Asynchronous Distributed Architecture**:
1.  **Frontend:** Vanilla JS + CSS (optimized for performance and premium aesthetics).
2.  **API Layer:** FastAPI (Python) handles requests and triggers background jobs.
3.  **Job Queue:** RabbitMQ manages task distribution.
4.  **Worker Layer:** Standalone Python processes (managed by `worker_manager.py`) perform the heavy AI lifting.
5.  **Storage:** 
    *   **MongoDB:** Stores user data, job status, and audit logs.
    *   **Local Filesystem:** Stores generated `.docx` files, `.json` section data, and `.png` diagrams.

---

## ⚡ 2. The SRS Generation Process (Step-by-Step)

When a user submits a "Generate SRS" request:

1.  **Submission (`srs_api.py`):** The API receives the request, stores the initial payload in MongoDB (`JobRepo`), and calculates a `job_id`.
2.  **Queuing (`publisher.py`):** A message is sent to RabbitMQ containing the `job_id`.
3.  **Worker Management (`worker_manager.py`):** 
    *   The manager checks the queue depth. 
    *   If the queue has messages, it spawns a new `worker.py` process (scaling up to 4 if needed).
4.  **Pipeline Initialization (`worker.py`):** The worker picks up the message, enters `handle_job()`, and starts the generation pipeline.
5.  **AI Agents (`srs_service.py`):** 
    *   **Phase 1-2:** Invokes specialized AI agents (e.g., `IntroductionAgent`, `SystemFeaturesAgent`) to generate content for 7 hierarchical sections.
    *   **Phase 3:** Invokes the `DiagramAgent` to generate Mermaid.js code for 4 system diagrams.
6.  **Document Assembly (`srs_document_generator.py`):** 
    *   Uses `python-docx` to create a professional Word document.
    *   Injects a dynamic Table of Contents, headers, footers, and rendered PNG diagrams.
7.  **Data Preservation & Indexing:**
    *   **JSON Storage:** Saves the full section data to `generated_srs/{user_id}/{project}_sections.json`. This is the "Working Draft" for future upgrades.
    *   **Metadata:** Creates `_meta.json` with project info and **Version 1 (Initial Generation)**.
    *   **RAG Index (`srs_rag_index.py`):** Builds a semantic search index (FAISS) for the document sections, allowing users to find parts of their SRS using natural language later.

---

## 🛠️ 3. The Upgrade & Sectioning System

Once a document is generated, it enters the **Section Upgrader** lifecycle:

### A. Navigation & Context
Users select a project from the dashboard. The system loads the `_meta.json` to verify the structure and counts.
*   **File:** `generated_srs_upgrade_router.py` -> `GET /list`

### B. AI Section Upgrading
Users can provide natural language instructions (e.g., *"Add a biometrics feature to the login section"*).
1.  **Lookup:** The system uses the **RAG index** to find the most relevant section if the user isn't navigated to one.
2.  **Processing (`section_upgrade_agent`):** The AI agent takes the **Current Section JSON**, the **User Instruction**, and a **Strict Pydantic Schema**.
3.  **JSON Patching:** The AI returns a "Patched JSON" that perfectly matches the required structure.
4.  **Validation:** The system runs a Pydantic `model_validate` check to ensure the AI didn't break the JSON format.
5.  **Preview:** The frontend shows a Side-by-Side Diff (`original` vs `upgraded`).

### C. Confirmation & "Rebuild"
When you confirm an upgrade, the `_sections.json` file is updated immediately. However, the Word document is **not** overwritten yet.
*   **The Rebuild Step:** Clicking "Rebuild Document" triggers the formal versioning process.

---

## 🕒 4. Versioning & Restore Logic

We use a **Snapshot-on-Build** pattern:

1.  **Backup Trigger (`generated_srs_upgrade_service.py`):** Before generating a new `.docx`, the system triggers `_create_version_backup`.
2.  **The Snapshot:**
    *   Copies `Project_sections.json` to `Project_sections_v{N}.json`.
    *   Copies current `Project_SRS.docx` to `Project_SRS_v{N}.docx`.
3.  **Identification:** A user-provided comment (e.g., *"Added payment module"*) linked to that version in `meta.json`.
4.  **Restore:** Clicking "Restore" swaps the historical JSON back to the primary "Working Draft" and re-runs the Document Generator to update the main `.docx`.

---

## 📂 5. Directory Structure Guide

| Path | Purpose |
| :--- | :--- |
| `srs_engine/core/routers/` | API endpoints (Generated Upgrader, History, Restore). |
| `srs_engine/core/services/` | Business logic for versioning and rebuilding documents. |
| `srs_engine/agents/upgrader_agents/` | AI Agent code for intelligent document modification. |
| `srs_engine/generated_srs/{user_id}/` | **Live Storage:** Where JSON/DOCX and Version Backups live. |
| `srs_engine/generated_images/` | Storage for rendered PNG diagrams. |
| `srs_engine/utils/` | Helpers for Document Generation, RAG Indexing, and Diagram Rendering. |

---

## 🛠️ 6. Troubleshooting Common Issues

*   **"331m ago" error:** Resolved by ensuring all timestamps are forced to UTC ISO format with the `Z` suffix.
*   **"Preview Failed":** Usually caused by an AI agent returning conversational text instead of raw JSON. Our **Regex Parser** in `section_upgrade_agent/agent.py` handles this.
*   **Connection Errors:** Managed by the **Global Connection Pool** in `worker.py` and `worker_manager.py`.

---

*This WIKI was generated to document the system state as of March 31, 2026.*