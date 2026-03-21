from __future__ import annotations

"""
section_analyser_agent
──────────────────────
Scores a single ParsedSection on 5 IEEE 830 dimensions and returns
structured analysis. One agent instance is created per run; multiple
sections are analysed by running the agent concurrently via asyncio.gather
in the upgrade service.

Pattern matches existing agents in technical_srs_agents/.
"""

import json
import asyncio
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .prompt import AGENT_DESCRIPTION, AGENT_INSTRUCTION
from ....schemas.upgrader_schemas.section_analyzer_agent_schema import SectionAnalysisOutput
from ....utils.globals import generate_content_config
from ....utils.model import groq_llm


# ── Agent factory (mirrors your existing pattern) ────────────────────────────

def create_section_analyser_agent() -> LlmAgent:
    return LlmAgent(
        name="section_analyser_agent",
        model=groq_llm,
        output_schema=SectionAnalysisOutput,
        description=AGENT_DESCRIPTION,
        instruction=AGENT_INSTRUCTION,
        output_key="section_analysis",
        generate_content_config=generate_content_config,
    )


# ── Single-section runner ────────────────────────────────────────────────────

async def analyse_single_section(
    section_id: str,
    heading: str,
    level: int,
    content: str,
    subsections_summary: str,
    document_context: dict,
    score_threshold: float = 6.5,
) -> SectionAnalysisOutput | None:
    """
    Run the analyser agent against one section.
    Returns SectionAnalysisOutput or None if parsing fails.
    """
    app_name = f"analyser_{section_id.replace('.', '_')}"
    session_id = "session_1"
    user_id = "system"

    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state={},
    )

    agent = create_section_analyser_agent()
    runner = Runner(
        app_name=app_name,
        agent=agent,
        session_service=session_service,
    )

    # Build the prompt payload for this section
    payload = {
        "section_id": section_id,
        "heading": heading,
        "level": level,
        "content": content if content.strip() else "[EMPTY — no content provided]",
        "subsections_summary": subsections_summary,
        "document_context": document_context,
        "score_threshold": score_threshold,
    }

    prompt = types.Content(
        role="user",
        parts=[types.Part(text=json.dumps(payload, ensure_ascii=False))],
    )

    raw_response: str | None = None

    # Retry up to 4 times on rate limit — rebuild runner fully each time
    # Wait times: 60s, 90s, 120s — enough for Groq's 1-min TPM window to reset
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
                print(f"[section_analyser_agent] Rate limit on {section_id}, "
                      f"retry {attempt + 1}/3 in {wait}s…")
                await asyncio.sleep(wait)

                # Rebuild session + runner from scratch — stale runner causes re-fails
                session_service = InMemorySessionService()
                await session_service.create_session(
                    app_name=app_name, user_id=user_id,
                    session_id=session_id, state={},
                )
                runner = Runner(
                    app_name=app_name,
                    agent=create_section_analyser_agent(),
                    session_service=session_service,
                )
            else:
                raise

    if not raw_response:
        return None

    try:
        # ADK with output_schema returns structured data directly
        if isinstance(raw_response, dict):
            return SectionAnalysisOutput(**raw_response)

        # Fallback: parse JSON string
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            lines = lines[1:] if lines[0].startswith("```") else lines
            lines = lines[:-1] if lines and lines[-1].strip().startswith("```") else lines
            cleaned = "\n".join(lines).strip()

        data = json.loads(cleaned)
        return SectionAnalysisOutput(**data)

    except Exception as e:
        print(f"[section_analyser_agent] Failed to parse response for {section_id}: {e}")
        return None


# ── Batch runner — processes sections in rate-limited batches ────────────────

async def analyse_all_sections(
    sections_payload: list[dict],
    document_context: dict,
    score_threshold: float = 6.5,
    batch_size: int = 5,
    batch_delay: float = 60.0,
    on_section_start: callable = None,
    on_section_done: callable = None,
) -> dict[str, SectionAnalysisOutput | None]:
    """
    Analyse sections in small batches to respect Groq TPM limits.

    on_section_start(section_id, heading, index, total) — called just before each agent call
    on_section_done(section_id, heading, index, total)  — called just after each agent call

    Returns: dict mapping section_id → SectionAnalysisOutput | None
    """
    output: dict[str, SectionAnalysisOutput | None] = {}
    total = len(sections_payload)

    async def _run_one(s: dict, global_index: int) -> tuple[str, SectionAnalysisOutput | None]:
        """Wraps single section: fires start callback → runs agent → fires done callback."""
        sid     = s["section_id"]
        heading = s["heading"]

        if on_section_start:
            await on_section_start(sid, heading, global_index, total)

        result = await analyse_single_section(
            section_id=sid,
            heading=heading,
            level=s["level"],
            content=s["content"],
            subsections_summary=s.get("subsections_summary", ""),
            document_context=document_context,
            score_threshold=score_threshold,
        )

        if on_section_done:
            await on_section_done(sid, heading, global_index, total)

        return sid, result

    for batch_start in range(0, total, batch_size):
        batch = sections_payload[batch_start: batch_start + batch_size]
        batch_num = batch_start // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size
        print(f"[section_analyser_agent] Batch {batch_num}/{total_batches} — {len(batch)} sections")

        tasks = [
            _run_one(s, batch_start + i + 1)
            for i, s in enumerate(batch)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                print(f"[section_analyser_agent] Exception: {result}")
            else:
                sid, analysis = result
                output[sid] = analysis

        if batch_start + batch_size < total:
            print(f"[section_analyser_agent] Rate limit pause {batch_delay}s...")
            await asyncio.sleep(batch_delay)

    return output