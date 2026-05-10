from __future__ import annotations

"""
core/services/srs_service.py

SRS generation service layer.

Phase 3 changes:
  - generate_srs() preserved for the worker. Router no longer calls it.
  - Router calls JobRepo.create_job() + publish_srs_job() instead.

Phase 4 changes:
  - generate_srs() now accepts an optional `on_progress` async callback:
      async def on_progress(progress: int, step: str) -> None
    The router never passes it so existing behaviour is 100% unchanged.
    The worker passes it to get granular progress updates into MongoDB.
"""

import asyncio
import json
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from google.adk.agents import ParallelAgent, SequentialAgent
from google.adk.sessions import InMemorySessionService

from srs_engine.agents.home_page_agents.auto_generate_agent import create_auto_generate_agent
from srs_engine.agents.home_page_agents.enhance_problem_statement_agent import (
    create_enhance_problem_statement_agent,
)
from srs_engine.agents.technical_srs_agents.assumptions_agent import (
    create_assumptions_agent as create_technical_srs_assumptions_agent,
)
from srs_engine.agents.technical_srs_agents.external_interfaces_agent import (
    create_external_interfaces_agent as create_technical_srs_external_interfaces_agent,
)
from srs_engine.agents.technical_srs_agents.glossary_agent import (
    create_glossary_agent as create_technical_srs_glossary_agent,
)
from srs_engine.agents.technical_srs_agents.introduction_agent import (
    create_introduction_agent as create_technical_srs_introduction_agent,
)
from srs_engine.agents.technical_srs_agents.nfr_agent import (
    create_nfr_agent as create_technical_srs_nfr_agent,
)
from srs_engine.agents.technical_srs_agents.overall_description_agent import (
    create_overall_description_agent as create_technical_srs_overall_description_agent,
)
from srs_engine.agents.technical_srs_agents.system_features_agent import (
    create_system_features_agent as create_technical_srs_system_features_agent,
)
from srs_engine.core.logging import (
    async_log_context,
    get_context_logger,
    log_execution_time,
    set_agent_id,
    set_session_id,
    set_user_id,
)
from srs_engine.utils.globals import (
    clean_and_parse_json,
    clean_interface_diagrams,
    create_enhance_prompt,
    create_prompt,
    create_runner,
    create_session,
    generated_response,
    get_session,
    render_mermaid_png,
)
from srs_engine.utils.srs_document_generator import generate_srs_document


logger = get_context_logger(__name__)
today = datetime.today().strftime("%m/%d/%Y")

# Type alias for the optional progress callback the worker supplies
ProgressCallback = Callable[[int, str], Awaitable[None]]


async def _noop_progress(progress: int, step: str) -> None:
    """Default no-op callback — used when no progress reporting is needed."""
    pass


async def create_technical_srs_agent():
    first_agent = SequentialAgent(
        name="first_agent",
        sub_agents=[
            ParallelAgent(
                name="first_parallel_agent",
                sub_agents=[
                    create_technical_srs_introduction_agent(),
                    create_technical_srs_overall_description_agent(),
                    create_technical_srs_system_features_agent(),
                    create_technical_srs_external_interfaces_agent(),
                    create_technical_srs_nfr_agent(),
                ],
                description="Handles Introduction, Overall Description, System Features, External Interfaces, and NFR sections.",
            )
        ],
    )

    second_agent = SequentialAgent(
        name="second_agent",
        sub_agents=[
            ParallelAgent(
                name="finalization_agent",
                sub_agents=[
                    create_technical_srs_glossary_agent(),
                    create_technical_srs_assumptions_agent(),
                ],
                description="Handles Glossary and Assumptions sections.",
            )
        ],
    )

    return first_agent, second_agent


def get_session_service(app: Any) -> InMemorySessionService:
    return app.state.session_service_stateful  # type: ignore[attr-defined]


async def enhance_problem_statement(app: Any, input_data: Any, user_id: str) -> dict[str, Any]:
    """Enhance problem statement using AI."""
    session_id = str(uuid.uuid4())

    async with async_log_context(session_id=session_id, user_id=user_id):
        logger.info("enhance_problem_statement | START | input validation")

        try:
            inputs = input_data.dict()
            project_name = inputs["project_name"]
            problem_statement = inputs["problem_statement"]

            logger.info(
                f"enhance_problem_statement | Input received | "
                f"project={project_name} | stmt_len={len(problem_statement)}"
            )

            initial_state = {
                "project_name": project_name,
                "problem_statement": problem_statement,
                "section_type": "PROBLEM_STATEMENT_ENHANCEMENT",
            }

            session_service_stateful = get_session_service(app)
            await create_session(session_service_stateful, project_name, user_id, session_id, initial_state)
            logger.debug("enhance_problem_statement | Session created")

            enhance_agent = create_enhance_problem_statement_agent()
            runner = await create_runner(enhance_agent, project_name, session_service_stateful)
            prompt = await create_enhance_prompt(project_name, problem_statement)

            response = await generated_response(runner, user_id, session_id, prompt)
            logger.debug("enhance_problem_statement | Agent response received")

            try:
                if isinstance(response, str):
                    parsed_response = json.loads(response)
                elif isinstance(response, dict):
                    parsed_response = response
                else:
                    parsed_response = response.dict() if hasattr(response, "dict") else dict(response)

                if "enhanced_problem_statement" not in parsed_response:
                    raise ValueError("Response missing 'enhanced_problem_statement' key")

                enhanced_statement = parsed_response["enhanced_problem_statement"]
                if not isinstance(enhanced_statement, str):
                    raise ValueError("'enhanced_problem_statement' must be a string")
                if len(enhanced_statement) < 50:
                    raise ValueError("Enhanced problem statement is too short (minimum 50 characters)")
                if len(enhanced_statement) > 1000:
                    raise ValueError("Enhanced problem statement is too long (maximum 1000 characters)")

                logger.info(
                    f"enhance_problem_statement | SUCCESS | "
                    f"enhanced_stmt_len={len(enhanced_statement)}"
                )
                return {"enhanced_problem_statement": enhanced_statement}

            except json.JSONDecodeError as e:
                logger.error(f"enhance_problem_statement | JSON Parse Error | {str(e)}")
                raise HTTPException(status_code=500, detail=f"Failed to parse agent response: {str(e)}")
            except ValueError as e:
                logger.error(f"enhance_problem_statement | Validation Error | {str(e)}")
                raise HTTPException(status_code=500, detail=f"Invalid response format: {str(e)}")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"enhance_problem_statement | FAILED | error={str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error in enhance_problem_statement: {str(e)}")


async def auto_generate_section(app: Any, input_data: Any, user_id: str) -> dict[str, Any]:
    """Auto-generate a section (features or user flow) using AI."""
    session_id = str(uuid.uuid4())

    async with async_log_context(session_id=session_id, user_id=user_id):
        logger.info("auto_generate_section | START | input validation")

        try:
            inputs = input_data.dict()
            project_name = inputs["project_name"]
            problem_statement = inputs["problem_statement"]
            section_type = inputs["section_type"]

            logger.info(
                f"auto_generate_section | Input received | "
                f"project={project_name} | section={section_type}"
            )
            internal_section_type = {
                "features": "CORE_FEATURES",
                "flow": "PRIMARY_USER_FLOW",
                "constraints": "SYSTEM_CONSTRAINTS",
                "assumptions": "KEY_ASSUMPTIONS"
            }.get(section_type)

            if not internal_section_type:
                raise ValueError(f"Unsupported section type: {section_type}")

            initial_state = {
                "project_name": project_name,
                "problem_statement": problem_statement,
                "section_type": internal_section_type,
            }

            session_service_stateful = get_session_service(app)
            await create_session(session_service_stateful, project_name, user_id, session_id, initial_state)

            agent = create_auto_generate_agent(internal_section_type)
            runner = await create_runner(agent, project_name, session_service_stateful)
            prompt = await create_prompt()

            response = await generated_response(runner, user_id, session_id, prompt)
            logger.debug("auto_generate_section | Agent response received")

            try:
                if isinstance(response, str):
                    data = json.loads(response)
                else:
                    data = response if isinstance(response, dict) else response.dict()

                if section_type == "features":
                    if "core_features" not in data:
                        raise ValueError("Response missing 'core_features' key")
                    logger.info(f"auto_generate_section | SUCCESS | section=features | feature_count={len(data['core_features'])}")
                    return {"core_features": data["core_features"]}
                
                elif section_type == "flow":
                    if "primary_user_flow" not in data:
                        raise ValueError("Response missing 'primary_user_flow' key")
                    logger.info(f"auto_generate_section | SUCCESS | section=flow | flow_len={len(data['primary_user_flow'])}")
                    return {"primary_user_flow": data["primary_user_flow"]}
                
                elif section_type == "constraints":
                    if "system_constraints" not in data:
                        raise ValueError("Response missing 'system_constraints' key")
                    constraints = data["system_constraints"]
                    logger.info(f"auto_generate_section | SUCCESS | section=constraints | count={len(constraints)}")
                    return {"system_constraints": "\n".join(constraints) if isinstance(constraints, list) else constraints}
                
                elif section_type == "assumptions":
                    if "key_assumptions" not in data:
                        raise ValueError("Response missing 'key_assumptions' key")
                    assumptions = data["key_assumptions"]
                    logger.info(f"auto_generate_section | SUCCESS | section=assumptions | count={len(assumptions)}")
                    return {"key_assumptions": "\n".join(assumptions) if isinstance(assumptions, list) else assumptions}



            except json.JSONDecodeError as e:
                logger.error(f"auto_generate_section | JSON Parse Error | {str(e)}")
                raise HTTPException(status_code=500, detail=f"Invalid JSON response: {str(e)}")
            except ValueError as e:
                logger.error(f"auto_generate_section | Validation Error | {str(e)}")
                raise HTTPException(status_code=500, detail=f"Invalid response format: {str(e)}")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"auto_generate_section | FAILED | error={str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


# ---------------------------------------------------------------------------
# Core generation pipeline — called by the worker, NOT by the router
# ---------------------------------------------------------------------------

async def generate_srs(
    app: Any,
    srs_data: Any,
    user_id: str,
    on_progress: ProgressCallback | None = None,
    db: Any = None,
) -> dict[str, Any]:
    """
    Generate complete SRS document with all sections and diagrams.

    NOTE: No longer called by the FastAPI router. Called by the worker process.

    Args:
        app:         Object with .state.session_service_stateful.
                     Worker passes a types.SimpleNamespace; FastAPI passes request.app.
        srs_data:    SRSRequest instance or plain dict with the full payload.
        user_id:     String user identifier.
        on_progress: Optional async def(progress: int, step: str) -> None.
                     Worker supplies this to write progress to MongoDB.
                     Defaults to a no-op so callers without progress reporting
                     are unaffected.
        db:          Optional MongoDB database instance (motor). If provided,
                     generated files are also uploaded to GridFS for persistence.
    """
    _progress = on_progress or _noop_progress
    session_id = str(uuid.uuid4())

    async with async_log_context(session_id=session_id, user_id=user_id):
        logger.info("generate_srs | START | Comprehensive SRS generation requested")

        try:
            inputs = srs_data.dict() if hasattr(srs_data, "dict") else srs_data
            project_name = inputs["project_identity"]["project_name"]
            author_list = inputs["project_identity"]["author"]
            organization_name = inputs["project_identity"]["organization"]
            system_context = inputs.get("system_context", {})

            logger.info(f"generate_srs | Project info | project={project_name} | org={organization_name}")

            initial_state = {"user_inputs": inputs}
            session_service_stateful = get_session_service(app)
            await create_session(session_service_stateful, project_name, user_id, session_id, initial_state)

            # ── Phase 1 ────────────────────────────────────────────────
            logger.info("generate_srs | PHASE 1 START | Loading 7 AI agents (5 parallel)...")
            await _progress(10, "Loading AI agents")

            first_agent, second_agent = await create_technical_srs_agent()
            runner = await create_runner(first_agent, project_name, session_service_stateful)
            prompt = await create_prompt()

            await _progress(20, "Generating core sections (Introduction, Features, NFR …)")
            logger.info("generate_srs | PHASE 1 IN PROGRESS | Running first 5 parallel agents...")
            await generated_response(runner, user_id, session_id, prompt)
            session = await get_session(session_service_stateful, project_name, user_id, session_id)
            logger.info("generate_srs | PHASE 1 COMPLETE")

            # ── Inter-phase wait ───────────────────────────────────────
            logger.debug("generate_srs | Waiting 60 seconds before phase 2...")
            await asyncio.sleep(60)

            # ── Phase 2 ────────────────────────────────────────────────
            await _progress(55, "Generating Glossary and Assumptions")
            logger.info("generate_srs | PHASE 2 START | Running final 2 parallel agents...")
            second_runner = await create_runner(second_agent, project_name, session_service_stateful)
            await generated_response(second_runner, user_id, session_id, prompt)
            session = await get_session(session_service_stateful, project_name, user_id, session_id)
            logger.info("generate_srs | PHASE 2 COMPLETE")

            # ── Extract sections ───────────────────────────────────────
            introduction_section = clean_and_parse_json(session.state.get("introduction_section", {}))
            overall_description_section = clean_and_parse_json(session.state.get("overall_description_section", {}))
            system_features_section = clean_and_parse_json(session.state.get("system_features_section", {}))
            external_interfaces_section = clean_interface_diagrams(
                clean_and_parse_json(session.state.get("external_interfaces_section", {}))
            )

            # ── Phase 3 — diagrams ─────────────────────────────────────
            await _progress(75, "Rendering architecture diagrams")
            logger.info("generate_srs | PHASE 3 START | Generating 4 architecture diagrams...")

            base_dir = Path(f"./srs_engine/generated_images/{user_id}")
            base_dir.mkdir(parents=True, exist_ok=True)

            image_paths = {}
            for key in ["user_interfaces", "hardware_interfaces", "software_interfaces", "communication_interfaces"]:
                if key in external_interfaces_section and "interface_diagram" in external_interfaces_section[key]:
                    diagram_code = external_interfaces_section[key]["interface_diagram"].get("code")
                    if diagram_code:
                        img_path = base_dir / f"{project_name}_{key}_diagram.png"
                        try:
                            render_mermaid_png(diagram_code, img_path)
                            image_paths[key] = str(img_path)
                        except Exception as e:
                            logger.warning(f"generate_srs | Failed to render diagram for {key}: {e}")
            logger.info("generate_srs | PHASE 3 COMPLETE | Interface diagrams generated")

            nfr_section         = clean_and_parse_json(session.state.get("nfr_section", {}))
            glossary_section    = clean_and_parse_json(session.state.get("glossary_section", {}))
            assumptions_section = clean_and_parse_json(session.state.get("assumptions_section", {}))

            # ── Phase 4 — document ─────────────────────────────────────
            await _progress(90, "Building Word document")
            logger.info("generate_srs | PHASE 4 START | Creating Word document (.docx)...")

            output_path = f"./srs_engine/generated_srs/{user_id}/{project_name}_SRS.docx"
            Path("./srs_engine/generated_srs").mkdir(exist_ok=True)
            Path(f"./srs_engine/generated_srs/{user_id}").mkdir(exist_ok=True)

            generated_path = generate_srs_document(
                project_name=project_name,
                introduction_section=introduction_section,
                overall_description_section=overall_description_section,
                system_features_section=system_features_section,
                external_interfaces_section=external_interfaces_section,
                nfr_section=nfr_section,
                glossary_section=glossary_section,
                assumptions_section=assumptions_section,
                image_paths=image_paths,
                output_path=output_path,
                authors=author_list,
                organization=organization_name,
            )
            logger.info(f"generate_srs | PHASE 4 COMPLETE | Document created | path={generated_path}")

            # ── Upload DOCX to GridFS (if db is available) ──────────────────────────────
            if db is not None:
                try:
                    from srs_engine.core.db.file_storage import FileStorage
                    fs = FileStorage(db)
                    docx_path_obj = Path(generated_path)
                    if docx_path_obj.exists():
                        docx_bytes = docx_path_obj.read_bytes()
                        await fs.save_file(
                            docx_bytes,
                            f"{project_name}_SRS.docx",
                            {
                                "type": "docx", 
                                "user_id": user_id, 
                                "project_name": project_name,
                                "domain": system_context.get("domain", "General")
                            },
                        )
                        logger.info(f"generate_srs | DOCX uploaded to GridFS | project={project_name}")
                except Exception as e:
                    logger.warning(f"generate_srs | GridFS DOCX upload failed (non-fatal): {e}")

            # ── Phase 5 — save JSON + build RAG index (NEW for upgrader) ──
            await _progress(95, "Saving section data for upgrader")
            logger.info("generate_srs | PHASE 5 START | Saving sections JSON + building RAG index")
            try:
                all_sections = {
                    "domain": "technical",
                    "project_name": project_name,
                    "introduction_section": introduction_section,
                    "overall_description_section": overall_description_section,
                    "system_features_section": system_features_section,
                    "external_interfaces_section": external_interfaces_section,
                    "nfr_section": nfr_section,
                    "glossary_section": glossary_section,
                    "assumptions_section": assumptions_section,
                }
                # ── Save to GridFS (NEW — for stateless Upgrader) ──
                if db is not None:
                    try:
                        from srs_engine.core.db.file_storage import FileStorage
                        fs = FileStorage(db)
                        await fs.save_json(
                            all_sections,
                            f"{project_name}_sections.json",
                            {"type": "sections_json", "user_id": user_id, "project_name": project_name}
                        )
                        logger.info(f"generate_srs | Sections JSON uploaded to GridFS | project={project_name}")
                    except Exception as e:
                        logger.warning(f"generate_srs | GridFS JSON upload failed (non-fatal): {e}")

                # Still save to disk for local dev/debugging (non-fatal if it fails in production)
                try:
                    _save_generated_srs_json(
                        user_id=user_id,
                        project_name=project_name,
                        sections=all_sections,
                        authors=author_list,
                        organization=organization_name,
                        docx_path=output_path,
                    )
                except Exception as e:
                    logger.warning(f"generate_srs | Local disk save failed: {e}")

                # Build RAG index (syncs to GridFS internally)
                try:
                    await _build_rag_index_safe(all_sections, user_id, project_name, db)
                except Exception as e:
                    logger.warning(f"generate_srs | RAG index build failed: {e}")

                # Upload sections + meta JSON to GridFS (if db is available)
                if db is not None:
                    try:
                        from srs_engine.core.db.file_storage import FileStorage
                        fs = FileStorage(db)
                        
                        # Save live files
                        await fs.save_file(
                            json.dumps(all_sections).encode(),
                            f"{project_name}_sections.json",
                            {"type": "sections_json", "user_id": user_id, "project_name": project_name}
                        )
                        
                        # Construct and save meta
                        meta = {
                            "project_name": project_name,
                            "domain": system_context.get("domain", "technical"),
                            "authors": author_list,
                            "organization": organization_name,
                            "generated_at": datetime.now(timezone.utc).isoformat() + "Z",
                            "modified_sections": [],
                            "versions": [
                                {
                                    "version": 1,
                                    "comment": "Initial generation",
                                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                                    "sections_backup": f"{project_name}_sections_v1.json",
                                    "docx_backup": f"{project_name}_SRS_v1.docx",
                                }
                            ],
                        }
                        await fs.save_file(
                            json.dumps(meta).encode(),
                            f"{project_name}_meta.json",
                            {"type": "meta_json", "user_id": user_id, "project_name": project_name}
                        )
                        
                        # Save v1 backups in GridFS
                        await fs.save_file(
                            json.dumps(all_sections).encode(),
                            f"{project_name}_sections_v1.json",
                            {"type": "version_sections_json", "user_id": user_id, "project_name": project_name, "version": 1}
                        )
                        
                        docx_path_obj = Path(output_path)
                        if docx_path_obj.exists():
                            docx_bytes = docx_path_obj.read_bytes()
                            await fs.save_file(
                                docx_bytes,
                                f"{project_name}_SRS_v1.docx",
                                {"type": "version_docx", "user_id": user_id, "project_name": project_name, "version": 1}
                            )

                        logger.info(f"generate_srs | GridFS persistence complete (including v1 history) | project={project_name}")
                    except Exception as e:
                        logger.warning(f"generate_srs | GridFS persistence failed: {e}")

                logger.info("generate_srs | PHASE 5 COMPLETE | Sections JSON + RAG index saved")
            except Exception as e:
                # Non-fatal — SRS generation still succeeds even if upgrader data fails
                logger.warning(f"generate_srs | PHASE 5 WARNING | Failed to save upgrader data: {e}")

            logger.info("generate_srs | SUCCESS | Full SRS generation completed!")

            return {"srs_document_path": generated_path}

        except Exception as e:
            logger.error(f"generate_srs | FAILED | error={str(e)}", exc_info=True)
            raise


# ── Upgrader helpers (save JSON + RAG) ────────────────────────────────────────

def _save_generated_srs_json(
    user_id: str,
    project_name: str,
    sections: dict,
    authors: list,
    organization: str,
    docx_path: str,
) -> None:
    """
    Save _sections.json and _meta.json alongside the generated .docx.
    Called after generate_srs_document() succeeds.

    BUG FIX: The previous implementation recorded version 1 in the metadata
    but pointed its 'sections_backup' at the live _sections.json file and its
    'docx_backup' at the live _SRS.docx.  Because _create_version_backup uses
    len(versions)+1 to pick the next version number, the first user-triggered
    rebuild would also try to create version 1 (collision), leaving two v1
    entries in the list and making restore_version fail for v1 (it expected a
    _sections_v1.json file that never existed).

    Fix: actually copy the freshly-generated files to _sections_v1.json /
    _SRS_v1.docx right here so the initial metadata entry is self-consistent
    with what every subsequent version entry looks like.
    """
    import shutil

    base_dir = Path(f"./srs_engine/generated_srs/{user_id}")
    base_dir.mkdir(parents=True, exist_ok=True)

    # ── Save live sections JSON ────────────────────────────────────────────────
    sections_path = base_dir / f"{project_name}_sections.json"
    with open(sections_path, "w", encoding="utf-8") as f:
        json.dump(sections, f, indent=2, ensure_ascii=False)

    # ── Create v1 backup files (the real fix) ─────────────────────────────────
    sections_v1_name = f"{project_name}_sections_v1.json"
    docx_v1_name = f"{project_name}_SRS_v1.docx"

    shutil.copy2(str(sections_path), str(base_dir / sections_v1_name))

    docx_src = Path(docx_path)
    docx_backed_up = False
    if docx_src.exists():
        shutil.copy2(str(docx_src), str(base_dir / docx_v1_name))
        docx_backed_up = True

    # ── Save meta JSON ─────────────────────────────────────────────────────────
    meta = {
        "project_name": project_name,
        "domain": sections.get("domain", "technical"),
        "authors": authors if isinstance(authors, list) else [authors],
        "organization": organization,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "docx_path": docx_path,
        "modified_sections": [],
        "section_keys": [
            "introduction_section",
            "overall_description_section",
            "system_features_section",
            "external_interfaces_section",
            "nfr_section",
            "glossary_section",
            "assumptions_section",
        ],
        # v1 now points at real backup files, not the live files.
        "versions": [
            {
                "version": 1,
                "comment": "Initial generation",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "sections_backup": sections_v1_name,
                "docx_backup": docx_v1_name if docx_backed_up else None,
            }
        ],
    }
    meta_path = base_dir / f"{project_name}_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    logger.info(f"_save_generated_srs_json | Saved sections + meta for {project_name}")


async def _build_rag_index_safe(sections: dict, user_id: str, project_name: str, db: Any = None) -> None:
    """
    Build FAISS RAG index. Non-fatal: logs warning if deps are missing.
    """
    try:
        from srs_engine.utils.srs_rag_index import build_rag_index
        await build_rag_index(sections, user_id, project_name, db)
    except ImportError:
        logger.warning(
            "_build_rag_index_safe | FAISS/sentence-transformers not installed — "
            "RAG index not built. Install with: pip install faiss-cpu sentence-transformers"
        )
    except Exception as e:
        logger.warning(f"_build_rag_index_safe | Failed to build RAG index: {e}")