from __future__ import annotations

"""
question_engine
───────────────
For each section flagged needs_upgrade=True, generates 1–3 targeted
clarification questions the user must answer before the Upgrade Writer runs.

Mirrors the section_analyser_agent pattern exactly.
"""

import json
import asyncio
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .prompt import AGENT_DESCRIPTION, AGENT_INSTRUCTION
from ....schemas.upgrader_schemas.question_engine_schema import QuestionEngineOutput, QuestionItem
from ....utils.globals import generate_content_config
from ....utils.model import groq_llm


# ── Agent factory ─────────────────────────────────────────────────────────────

def create_question_engine_agent() -> LlmAgent:
    return LlmAgent(
        name="question_engine_agent",
        model=groq_llm,
        output_schema=QuestionEngineOutput,
        description=AGENT_DESCRIPTION,
        instruction=AGENT_INSTRUCTION,
        output_key="section_questions",
        generate_content_config=generate_content_config,
    )


# ── Single-section question generator ────────────────────────────────────────

async def generate_questions_for_section(
    section_id: str,
    heading: str,
    content: str,
    flags: list[str],
    scores: dict,
    brief_summary: str,
) -> list[QuestionItem]:
    """
    Generate clarifying questions for one flagged section.
    Returns list of QuestionItem (1–3 items). Empty list on failure.
    """
    app_name = f"question_engine_{section_id.replace('.', '_')}"
    session_id = "session_1"
    user_id = "system"

    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state={},
    )

    agent = create_question_engine_agent()
    runner = Runner(
        app_name=app_name,
        agent=agent,
        session_service=session_service,
    )

    payload = {
        "section_id": section_id,
        "heading": heading,
        "content": content if content.strip() else "[EMPTY]",
        "flags": flags,
        "scores": scores,
        "brief_summary": brief_summary,
    }

    prompt = types.Content(
        role="user",
        parts=[types.Part(text=json.dumps(payload, ensure_ascii=False))],
    )

    raw_response: str | None = None

    # Retry up to 4 times on rate limit — rebuild runner fully each time
    for attempt in range(4):
        try:
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=prompt,
            ):
                if event.is_final_response():
                    raw_response = event.content.parts[0].text
            break  # success — exit retry loop

        except Exception as e:
            is_rate_limit = "rate_limit" in str(e).lower() or "429" in str(e)
            if is_rate_limit and attempt < 3:
                wait = 60 + attempt * 30   # 60s, 90s, 120s
                print(f"[question_engine] Rate limit on {section_id}, "
                      f"retry {attempt + 1}/3 in {wait}s…")
                await asyncio.sleep(wait)

                # Rebuild session + runner from scratch
                session_service = InMemorySessionService()
                await session_service.create_session(
                    app_name=app_name, user_id=user_id,
                    session_id=session_id, state={},
                )
                runner = Runner(
                    app_name=app_name,
                    agent=create_question_engine_agent(),
                    session_service=session_service,
                )
            else:
                raise

    if not raw_response:
        return []

    try:
        # Handle ADK structured output (dict with "questions" key)
        if isinstance(raw_response, dict):
            output = QuestionEngineOutput(**raw_response)
            return output.questions

        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            lines = lines[1:] if lines[0].startswith("```") else lines
            lines = lines[:-1] if lines and lines[-1].strip().startswith("```") else lines
            cleaned = "\n".join(lines).strip()

        data = json.loads(cleaned)

        # Agent may return a list directly or wrapped in {"questions": [...]}
        if isinstance(data, list):
            return [QuestionItem(**q) for q in data]
        if isinstance(data, dict) and "questions" in data:
            return [QuestionItem(**q) for q in data["questions"]]

        return []

    except Exception as e:
        print(f"[question_engine] Failed to parse questions for {section_id}: {e}")
        return []


# ── Batch runner — generates questions in rate-limited batches ───────────────

async def generate_all_questions(
    flagged_sections: list[dict],
    batch_size: int = 8,
    batch_delay: float = 60.0,
    on_section_start: callable = None,
    on_section_done: callable = None,
) -> dict[str, list[QuestionItem]]:
    """
    Generate questions in small batches to respect Groq TPM limits.

    on_section_start(section_id, heading, index, total) — fires before each agent call
    on_section_done(section_id, heading, index, total)  — fires after each agent call

    Returns: dict mapping section_id → list[QuestionItem]
    """
    output: dict[str, list[QuestionItem]] = {}
    total = len(flagged_sections)

    async def _run_one(s: dict, global_index: int) -> tuple[str, list[QuestionItem]]:
        sid     = s["section_id"]
        heading = s["heading"]

        if on_section_start:
            await on_section_start(sid, heading, global_index, total)

        result = await generate_questions_for_section(
            section_id=sid,
            heading=heading,
            content=s["content"],
            flags=s["flags"],
            scores=s["scores"],
            brief_summary=s["brief_summary"],
        )

        if on_section_done:
            await on_section_done(sid, heading, global_index, total)

        return sid, result

    for batch_start in range(0, total, batch_size):
        batch = flagged_sections[batch_start: batch_start + batch_size]
        batch_num = batch_start // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size
        print(f"[question_engine] Batch {batch_num}/{total_batches} — {len(batch)} sections")

        tasks = [
            _run_one(s, batch_start + i + 1)
            for i, s in enumerate(batch)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                print(f"[question_engine] Exception: {result}")
            else:
                sid, questions = result
                output[sid] = questions

        if batch_start + batch_size < total:
            print(f"[question_engine] Rate limit pause {batch_delay}s...")
            await asyncio.sleep(batch_delay)

    return output