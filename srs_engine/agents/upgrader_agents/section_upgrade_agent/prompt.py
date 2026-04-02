"""
section_upgrade_agent/prompt.py
───────────────────────────────
Builds the upgrade prompt for both text and diagram section types.
"""

from __future__ import annotations

AGENT_DESCRIPTION = (
    "An expert SRS section upgrader that modifies a single section's JSON "
    "based on a user instruction while preserving the schema structure."
)

AGENT_INSTRUCTION = """\
You are an expert Software Requirements Specification (SRS) editor.

### CRITICAL: RESPONSE FORMAT
1. YOUR ENTIRE RESPONSE MUST BE A SINGLE VALID JSON OBJECT.
2. DO NOT INCLUDE ANY PREAMBLE, POSTAMBLE, OR CONVERSATIONAL TEXT.
3. DO NOT SAY "Here is the upgrade" or similar.
4. START YOUR RESPONSE WITH `{` AND END WITH `}`.

## Rules
- Return the COMPLETE upgraded section JSON (not just the changed fields).
- Preserve all existing fields and their structure exactly unless instructed otherwise.
- Ensure the output strictly follows the schema description provided.

## Output Structure
Return a JSON object with exactly these three fields:
{
    "upgraded_section_json": { ... },   // the complete upgraded section
    "changes_summary": "...",           // 1-2 sentence summary of what changed
    "fields_modified": ["field.subfield", ...]  // dot-notation paths of modified fields
}
"""


def build_upgrade_prompt(
    section_key: str,
    section_type: str,
    user_instruction: str,
    current_section_json: dict,
    schema_description: str,
) -> str:
    """
    Build the user-message payload for the upgrade agent.

    Returns a JSON string that the agent receives as input.
    """
    import json

    payload = {
        "section_key": section_key,
        "section_type": section_type,
        "user_instruction": user_instruction,
        "current_section_json": current_section_json,
        "schema_description": schema_description,
    }

    return json.dumps(payload, ensure_ascii=False, indent=2)
