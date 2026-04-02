"""
section_upgrade_agent/agent.py
──────────────────────────────
Single ADK agent that upgrades one SRS section based on a user instruction.
Pattern matches existing agents in technical_srs_agents/ and upgrader_agents/.
"""

from __future__ import annotations

import json
import re
import asyncio
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .prompt import AGENT_DESCRIPTION, AGENT_INSTRUCTION, build_upgrade_prompt
from ....utils.globals import generate_content_config
from ....utils.model import groq_llm


# ── Agent factory ────────────────────────────────────────────────────────────

def create_section_upgrade_agent() -> LlmAgent:
    """Create a fresh instance of the section upgrade agent."""
    return LlmAgent(
        name="section_upgrade_agent",
        model=groq_llm,
        description=AGENT_DESCRIPTION,
        instruction=AGENT_INSTRUCTION,
        output_key="section_upgrade_result",
        # Removed generate_content_config (Gemini-specific) for Groq/LiteLLM compatibility
    )


# ── Single-section runner ────────────────────────────────────────────────────

async def run_section_upgrade(
    section_key: str,
    section_type: str,
    user_instruction: str,
    current_section_json: dict,
    schema_description: str,
) -> dict | None:
    """
    Run the upgrade agent against one section.

    Returns a dict with keys:
        - upgraded_section_json (dict)
        - changes_summary (str)
        - fields_modified (list[str])

    Returns None if parsing fails after retries.
    """
    app_name = f"upgrader_{section_key}"
    session_id = "session_1"
    user_id = "system"

    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state={},
    )

    agent = create_section_upgrade_agent()
    runner = Runner(
        app_name=app_name,
        agent=agent,
        session_service=session_service,
    )

    # Build the prompt payload
    prompt_text = build_upgrade_prompt(
        section_key=section_key,
        section_type=section_type,
        user_instruction=user_instruction,
        current_section_json=current_section_json,
        schema_description=schema_description,
    )
    
    print(f"[section_upgrade_agent] RUNNING UPGRADE for {section_key}...")
    print(f"[section_upgrade_agent] Prompt length: {len(prompt_text)}")

    prompt = types.Content(
        role="user",
        parts=[types.Part(text=prompt_text)],
    )

    raw_response: str | None = None

    # Retry up to 4 times on rate limit
    for attempt in range(4):
        try:
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=prompt,
            ):
                if event.is_final_response():
                    raw_response = event.content.parts[0].text
            break

        except Exception as e:
            is_rate_limit = "rate_limit" in str(e).lower() or "429" in str(e)
            if is_rate_limit and attempt < 3:
                wait = 60 + attempt * 30
                print(
                    f"[section_upgrade_agent] Rate limit on {section_key}, "
                    f"retry {attempt + 1}/3 in {wait}s…"
                )
                await asyncio.sleep(wait)

                # Rebuild session + runner
                session_service = InMemorySessionService()
                await session_service.create_session(
                    app_name=app_name,
                    user_id=user_id,
                    session_id=session_id,
                    state={},
                )
                runner = Runner(
                    app_name=app_name,
                    agent=create_section_upgrade_agent(),
                    session_service=session_service,
                )
            else:
                raise

    if not raw_response:
        print(f"[section_upgrade_agent] ERROR: No raw_response received for {section_key}")
        return None

    # Parse the response
    try:
        print(f"[section_upgrade_agent] Parsing response for {section_key}...")
        
        # 1. If it's already a dict (some LiteLLM handlers do this)
        if isinstance(raw_response, dict):
            data = raw_response
        else:
            cleaned = raw_response.strip()
            
            # 2. Extract JSON from markdown code block if present
            # Matches ```json { ... } ``` or ``` { ... } ```
            json_match = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", cleaned, re.MULTILINE)
            if json_match:
                cleaned = json_match.group(1).strip()
            else:
                # 3. Fallback: find first { and last }
                start = cleaned.find("{")
                end = cleaned.rfind("}")
                if start != -1 and end != -1:
                    cleaned = cleaned[start : end + 1]
            
            data = json.loads(cleaned)

        # Validate expected keys
        if "upgraded_section_json" not in data:
            print(f"[section_upgrade_agent] ERROR: Response missing 'upgraded_section_json' for {section_key}")
            return None

        print(f"[section_upgrade_agent] SUCCESS: Parsed {section_key} upgrade")
        return {
            "upgraded_section_json": data["upgraded_section_json"],
            "changes_summary": data.get("changes_summary", "Section upgraded."),
            "fields_modified": data.get("fields_modified", []),
        }

    except Exception as e:
        print(f"[section_upgrade_agent] FAILED to parse response for {section_key}: {e}")
        # Print a snippet of what we tried to parse
        snip = str(raw_response)[:400].replace("\n", " ")
        print(f"[section_upgrade_agent] Raw snippet: {snip}...")
        return None
