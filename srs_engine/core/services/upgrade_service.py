from __future__ import annotations

"""
upgrade_service.py
──────────────────
Orchestrates the SRS Upgrader pipeline:

  1. create_upgrade_session()   → snapshot all sections from parsed doc
  2. run_analysis()             → score every section via section_analyser_agent
  3. run_question_generation()  → generate questions for flagged sections
  4. submit_answers()           → store user answers, mark sections as answered
  5. get_session()              → load current session state
  6. assemble_final_document()  → merge accepted upgrades back into doc tree

Sessions are stored as JSON at:
    upgrade_sessions/{user_id}/{file_id}.json

The original ParsedSection tree is NEVER mutated. All changes live in the session.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException

from srs_engine.schemas.upload_schemas.parse_schema import (
    ParsedSection,
    UnifiedDocumentJSON,
)
from srs_engine.schemas.upgrader_schemas.upgrade_session_schema import (
    AnswerSubmission,
    SectionScore,
    SectionUpgradeRecord,
    UpgradeQuestion,
    UpgradeSession,
)
from srs_engine.agents.upgrader_agents.section_analyzer_agent import analyse_all_sections
from srs_engine.agents.upgrader_agents.question_engine import generate_all_questions
from srs_engine.core.db.file_storage import FileStorage
from motor.motor_asyncio import AsyncIOMotorDatabase
from srs_engine.core.services.parse_service import get_parsed_document

def _emit(file_id: str, event: dict) -> None:
    """Fire-and-forget progress event. Import is lazy to avoid circular import."""
    import asyncio
    try:
        from srs_engine.core.routers.upgrade_router import put_progress
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(put_progress(file_id, event))
    except Exception:
        pass  # progress is best-effort — never block the pipeline


# ── Session persistence ────────────────────────────────────────────────────────

async def _load_session(db: AsyncIOMotorDatabase, user_id: str, file_id: str) -> UpgradeSession:
    storage = FileStorage(db)
    data = await storage.get_json({"type": "upgrade_session", "user_id": user_id, "file_id": file_id})
    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"Upgrade session not found for file {file_id}. Call /upgrade/srs/{{file_id}}/analyse first.",
        )
    return UpgradeSession.model_validate(data)


async def _save_session(db: AsyncIOMotorDatabase, session: UpgradeSession, user_id: str) -> None:
    session.updated_at = datetime.now(timezone.utc)
    storage = FileStorage(db)
    await storage.save_json(
        session.model_dump(),
        f"{session.file_id}_session.json",
        {"type": "upgrade_session", "user_id": user_id, "file_id": session.file_id}
    )


async def _load_parsed_doc(db: AsyncIOMotorDatabase, user_id: str, file_id: str) -> UnifiedDocumentJSON:
    try:
        return await get_parsed_document(db, user_id, file_id)
    except Exception:
        raise HTTPException(
            status_code=404,
            detail=f"Parsed document not found for file {file_id}. Go back and click 'Parse Document' first.",
        )


# ── Tree flattening helpers ────────────────────────────────────────────────────

def _flatten_sections(
    sections: list[ParsedSection],
    parent_summary: str = "",
) -> list[dict]:
    """
    Recursively flatten the ParsedSection tree into a flat list of dicts
    suitable for passing to agents. Preserves all section_id / heading / level.
    """
    flat: list[dict] = []

    for s in sections:
        # Build a brief summary of immediate children for context
        sub_summary = (
            ", ".join(f'"{sub.heading}"' for sub in s.subsections)
            if s.subsections
            else "none"
        )

        flat.append({
            "section_id": s.section_id,
            "heading": s.heading,
            "level": s.level,
            "content": s.content,
            "subsections_summary": f"Subsections: {sub_summary}",
        })

        # Recurse into subsections
        flat.extend(_flatten_sections(s.subsections))

    return flat


def _build_document_context(doc: UnifiedDocumentJSON) -> dict:
    """
    Extract high-level facts about the document for the analyser's
    consistency checking (without sending the full document each time).
    """
    top_level_headings = [s.heading for s in doc.sections if s.level == 1]
    all_headings = []

    def collect(sections: list[ParsedSection]) -> None:
        for s in sections:
            all_headings.append(f"{s.section_id} {s.heading}")
            collect(s.subsections)

    collect(doc.sections)

    return {
        "filename": doc.metadata.original_filename,
        "word_count": doc.metadata.word_count,
        "top_level_sections": top_level_headings,
        "all_section_ids": all_headings[:40],  # cap to avoid huge prompts
    }


# ── 1. Create session ──────────────────────────────────────────────────────────

async def create_upgrade_session(
    db: AsyncIOMotorDatabase,
    user_id: str,
    file_id: str,
) -> UpgradeSession:
    """
    Snapshot all ParsedSections from the parsed doc into an UpgradeSession.
    original_content is locked in here and never changed afterward.
    """
    doc = await _load_parsed_doc(db, user_id, file_id)
    flat = _flatten_sections(doc.sections)

    records = [
        SectionUpgradeRecord(
            section_id=s["section_id"],
            heading=s["heading"],
            level=s["level"],
            original_content=s["content"],  # snapshot — immutable
        )
        for s in flat
    ]

    session = UpgradeSession(
        file_id=file_id,
        user_id=user_id,
        original_filename=doc.metadata.original_filename,
        sections=records,
        pipeline_status="created",
    )

    await _save_session(db, session, user_id)
    return session


# ── 2. Run analysis ────────────────────────────────────────────────────────────

async def run_analysis(
    db: AsyncIOMotorDatabase,
    user_id: str,
    file_id: str,
    score_threshold: float = 6.5,
) -> UpgradeSession:
    """
    Score every section using section_analyser_agent (concurrently).
    Updates each SectionUpgradeRecord with scores, flags, needs_upgrade.
    """
    # Auto-create session if missing — so frontend can call /analyse directly
    try:
        session = await _load_session(db, user_id, file_id)
    except Exception:
        session = await create_upgrade_session(db, user_id=user_id, file_id=file_id)

    doc = await _load_parsed_doc(db, user_id, file_id)

    session.pipeline_status = "analysing"
    await _save_session(db, session, user_id)

    flat = _flatten_sections(doc.sections)
    document_context = _build_document_context(doc)

    total_sections = len(flat)
    _emit(file_id, {
        "type": "start",
        "stage": "analysis",
        "total": total_sections,
        "message": f"Starting analysis of {total_sections} sections…"
    })

    # Callbacks — fire SSE events before AND after each section
    async def on_start(sid: str, heading: str, index: int, total: int) -> None:
        _emit(file_id, {
            "type": "section_start",
            "stage": "analysis",
            "section_id": sid,
            "heading": heading,
            "index": index,
            "total": total,
        })

    async def on_done(sid: str, heading: str, index: int, total: int) -> None:
        _emit(file_id, {
            "type": "section_done",
            "stage": "analysis",
            "section_id": sid,
            "heading": heading,
            "index": index,
            "total": total,
        })

    results = await analyse_all_sections(
        sections_payload=flat,
        document_context=document_context,
        score_threshold=score_threshold,
        on_section_start=on_start,
        on_section_done=on_done,
    )

    # Map results back into session records
    record_map = {r.section_id: r for r in session.sections}

    for idx, section_dict in enumerate(flat):
        sid = section_dict["section_id"]
        record = record_map.get(sid)
        analysis = results.get(sid)

        _emit(file_id, {
            "type": "section_done",
            "stage": "analysis",
            "section_id": sid,
            "heading": section_dict.get("heading", sid),
            "index": idx + 1,
            "total": len(flat),
        })

        if record is None:
            continue

        if analysis is None:
            # Agent failed for this section — mark as kept, don't block pipeline
            record.flags = ["Analysis failed — section kept as-is"]
            record.needs_upgrade = False
            record.status = "kept"
            continue

        # Store scores
        record.score = SectionScore(
            completeness=analysis.scores.completeness,
            clarity=analysis.scores.clarity,
            ieee_compliance=analysis.scores.ieee_compliance,
            testability=analysis.scores.testability,
            consistency=analysis.scores.consistency,
        )
        record.flags = analysis.flags

        # Apply threshold — also force upgrade if content is empty
        content_empty = not section_dict["content"].strip()
        overall = record.score.overall
        any_dim_critical = any(
            v <= 3.0 for v in [
                analysis.scores.completeness,
                analysis.scores.clarity,
                analysis.scores.ieee_compliance,
                analysis.scores.testability,
                analysis.scores.consistency,
            ]
        )

        record.needs_upgrade = (
            analysis.needs_upgrade
            or overall < score_threshold
            or any_dim_critical
            or content_empty
        )

        record.status = "pending" if record.needs_upgrade else "kept"

    session.pipeline_status = "analysed"
    await _save_session(db, session, user_id)

    flagged_count = sum(1 for s in session.sections if s.needs_upgrade)
    _emit(file_id, {
        "type": "stage_done",
        "stage": "analysis",
        "flagged": flagged_count,
        "total": len(session.sections),
        "message": f"Analysis complete — {flagged_count} sections flagged for upgrade",
    })
    return session


# ── 3. Generate questions ──────────────────────────────────────────────────────

async def run_question_generation(
    db: AsyncIOMotorDatabase,
    user_id: str,
    file_id: str,
) -> UpgradeSession:
    """
    For all sections with needs_upgrade=True and status="pending",
    generate clarifying questions via question_engine (concurrently).
    """
    session = await _load_session(db, user_id, file_id)
    session.pipeline_status = "questioning"
    await _save_session(db, session, user_id)

    # Build payload for flagged sections only
    flagged = [
        {
            "section_id": r.section_id,
            "heading": r.heading,
            "content": r.original_content,
            "flags": r.flags,
            "scores": r.score.model_dump() if r.score else {},
            "brief_summary": r.flags[0] if r.flags else "Section needs improvement",
        }
        for r in session.sections
        if r.needs_upgrade and r.status == "pending"
    ]

    if not flagged:
        session.pipeline_status = "ready"
        await _save_session(db, session, user_id)
        return session

    _emit(file_id, {
        "type": "start",
        "stage": "questions",
        "total": len(flagged),
        "message": f"Generating clarification questions for {len(flagged)} flagged sections…"
    })

    async def on_q_start(sid: str, heading: str, index: int, total: int) -> None:
        _emit(file_id, {
            "type": "section_start",
            "stage": "questions",
            "section_id": sid,
            "heading": heading,
            "index": index,
            "total": total,
        })

    async def on_q_done(sid: str, heading: str, index: int, total: int) -> None:
        _emit(file_id, {
            "type": "section_done",
            "stage": "questions",
            "section_id": sid,
            "heading": heading,
            "index": index,
            "total": total,
        })

    questions_by_section = await generate_all_questions(
        flagged_sections=flagged,
        on_section_start=on_q_start,
        on_section_done=on_q_done,
    )

    record_map = {r.section_id: r for r in session.sections}

    for sid, question_items in questions_by_section.items():
        record = record_map.get(sid)
        if record is None:
            continue

        if not question_items:
            # No questions generated — mark as answered so writer can proceed
            record.status = "answered"
            continue

        record.questions = [
            UpgradeQuestion(
                question_id=q.question_id,
                question=q.question,
                dimension=q.dimension,
            )
            for q in question_items
        ]
        record.status = "questioned"

    session.pipeline_status = "questioning"
    await _save_session(db, session, user_id)

    _emit(file_id, {
        "type": "done",
        "stage": "questions",
        "message": "Questions generated — ready for your answers",
    })
    return session


# ── 4. Submit answers ──────────────────────────────────────────────────────────

async def submit_answers(
    db: AsyncIOMotorDatabase,
    user_id: str,
    file_id: str,
    submissions: list[AnswerSubmission],
) -> UpgradeSession:
    """
    Store user answers for one or more sections.
    When all questions in a section are answered, marks it as "answered".
    When all flagged sections are answered, advances pipeline to "ready".
    """
    session = await _load_session(db, user_id, file_id)
    record_map = {r.section_id: r for r in session.sections}

    for submission in submissions:
        record = record_map.get(submission.section_id)
        if record is None:
            continue

        for q in record.questions:
            if q.question_id in submission.answers:
                q.answer = submission.answers[q.question_id]
                q.answered = True

        if record.all_questions_answered:
            record.status = "answered"

    # Advance pipeline if all flagged sections are now answered
    all_answered = all(
        r.status in ("answered", "kept", "rejected")
        for r in session.sections
        if r.needs_upgrade
    )
    if all_answered:
        session.pipeline_status = "ready"

    await _save_session(db, session, user_id)
    return session


# ── 5. Get session ─────────────────────────────────────────────────────────────

async def get_upgrade_session(db: AsyncIOMotorDatabase, user_id: str, file_id: str) -> UpgradeSession:
    return await _load_session(db, user_id, file_id)


# ── 6. Accept / reject sections ───────────────────────────────────────────────

async def update_section_status(
    db: AsyncIOMotorDatabase,
    user_id: str,
    file_id: str,
    section_id: str,
    action: str,               # "accept" | "reject" | "edit"
    edited_content: str = "",
) -> UpgradeSession:
    """
    User accepts, rejects, or edits the upgraded content for a section.
    """
    session = await _load_session(db, user_id, file_id)
    record = next((r for r in session.sections if r.section_id == section_id), None)

    if record is None:
        raise HTTPException(status_code=404, detail=f"Section {section_id} not found in session.")

    if action == "accept":
        record.status = "accepted"
    elif action == "reject":
        record.status = "rejected"
    elif action == "edit":
        record.user_edited_content = edited_content
        record.status = "edited"
    else:
        raise HTTPException(status_code=422, detail=f"Unknown action '{action}'. Use accept/reject/edit.")

    # Check if all reviewed
    all_done = all(
        r.status in ("accepted", "edited", "rejected", "kept")
        for r in session.sections
    )
    if all_done:
        session.pipeline_status = "complete"

    await _save_session(db, session, user_id)
    return session


# ── 7. Assemble final document ─────────────────────────────────────────────────

async def assemble_final_document(
    db: AsyncIOMotorDatabase,
    user_id: str,
    file_id: str,
) -> UnifiedDocumentJSON:
    """
    Merge accepted upgrades back into the original parsed document tree.
    Headings, section IDs, levels, and tables ALWAYS come from the original tree.
    Only content is selectively replaced from the session using final_content.
    """
    session = await _load_session(db, user_id, file_id)
    doc = await _load_parsed_doc(db, user_id, file_id)
    record_map = {r.section_id: r for r in session.sections}

    def patch_section(s: ParsedSection) -> ParsedSection:
        record = record_map.get(s.section_id)
        return ParsedSection(
            section_id=s.section_id,      # always from original tree
            heading=s.heading,            # always from original tree — never LLM
            level=s.level,               # always from original tree
            tables=s.tables,             # always from original tree — never LLM
            content=(
                record.final_content      # uses the property: edited > accepted > original
                if record is not None
                else s.content
            ),
            subsections=[patch_section(sub) for sub in s.subsections],
        )

    patched_sections = [patch_section(s) for s in doc.sections]

    # Rebuild raw_text from patched sections
    def collect_text(sections: list[ParsedSection]) -> str:
        parts = []
        for s in sections:
            if s.heading:
                parts.append(s.heading)
            if s.content:
                parts.append(s.content)
            parts.append(collect_text(s.subsections))
        return "\n".join(filter(None, parts))

    return UnifiedDocumentJSON(
        metadata=doc.metadata,
        sections=patched_sections,
        raw_text=collect_text(patched_sections),
        tables=doc.tables,
    )