from google.adk.agents import LlmAgent
from .prompt import (
    CORE_FEATURES_AGENT_DESCRIPTION, CORE_FEATURES_AGENT_INSTRUCTION,
    PRIMARY_USER_FLOW_AGENT_DESCRIPTION, PRIMARY_USER_FLOW_AGENT_INSTRUCTION,
    SYSTEM_CONSTRAINTS_AGENT_DESCRIPTION, SYSTEM_CONSTRAINTS_AGENT_INSTRUCTION,
    KEY_ASSUMPTIONS_AGENT_DESCRIPTION, KEY_ASSUMPTIONS_AGENT_INSTRUCTION
)
from ....schemas.home_page_schemas.core_features_schema import CORE_FEATURES_Section
from ....schemas.home_page_schemas.primary_user_flow_schema import PRIMARY_USER_FLOW_Section
from ....schemas.home_page_schemas.system_constraints_schema import SYSTEM_CONSTRAINTS_Section
from ....schemas.home_page_schemas.key_assumptions_schema import KEY_ASSUMPTIONS_Section
from ....utils.globals import generate_content_config
from ....utils.model import *

SECTION_SCHEMA_MAP = {
    "CORE_FEATURES": CORE_FEATURES_Section,
    "PRIMARY_USER_FLOW": PRIMARY_USER_FLOW_Section,
    "SYSTEM_CONSTRAINTS": SYSTEM_CONSTRAINTS_Section,
    "KEY_ASSUMPTIONS": KEY_ASSUMPTIONS_Section,
}

def create_auto_generate_agent(section: str):
    schema = SECTION_SCHEMA_MAP.get(section)
    
    if section == "CORE_FEATURES":
        desc = CORE_FEATURES_AGENT_DESCRIPTION
        instr = CORE_FEATURES_AGENT_INSTRUCTION
    elif section == "PRIMARY_USER_FLOW":
        desc = PRIMARY_USER_FLOW_AGENT_DESCRIPTION
        instr = PRIMARY_USER_FLOW_AGENT_INSTRUCTION
    elif section == "SYSTEM_CONSTRAINTS":
        desc = SYSTEM_CONSTRAINTS_AGENT_DESCRIPTION
        instr = SYSTEM_CONSTRAINTS_AGENT_INSTRUCTION
    elif section == "KEY_ASSUMPTIONS":
        desc = KEY_ASSUMPTIONS_AGENT_DESCRIPTION
        instr = KEY_ASSUMPTIONS_AGENT_INSTRUCTION
    else:
        raise ValueError(f"Unknown section type: {section}")

    return LlmAgent(
        name="auto_generate_agent",
        model=groq_llm_2,
        output_schema=schema,
        description=desc,
        instruction=instr,
        output_key=f"{section}_output",
        generate_content_config=generate_content_config
    )
