from google.adk.agents import LlmAgent
from .prompt import CORE_FEATURES_AGENT_DESCRIPTION , CORE_FEATURES_AGENT_INSTRUCTION , PRIMARY_USER_FLOW_AGENT_DESCRIPTION , PRIMARY_USER_FLOW_AGENT_INSTRUCTION
from ....schemas.home_page_schemas.core_features_schema import CORE_FEATURES_Section
from ....schemas.home_page_schemas.primary_user_flow_schema import PRIMARY_USER_FLOW_Section
from ....utils.globals import generate_content_config
from ....utils.model import *



SECTION_SCHEMA_MAP = {
    "CORE_FEATURES": CORE_FEATURES_Section,
    "PRIMARY_USER_FLOW": PRIMARY_USER_FLOW_Section,
}



## For app

def create_auto_generate_agent(section: str):
    schema = SECTION_SCHEMA_MAP.get(section)
    
    if section == "CORE_FEATURES":
        desc = CORE_FEATURES_AGENT_DESCRIPTION
        instr = CORE_FEATURES_AGENT_INSTRUCTION
    else:
        desc = PRIMARY_USER_FLOW_AGENT_DESCRIPTION
        instr = PRIMARY_USER_FLOW_AGENT_INSTRUCTION

    return LlmAgent(
        name="auto_generate_agent",
        model=groq_llm_2,
        output_schema=schema,
        description=desc,
        instruction=instr,
        output_key=f"{section}_output",
        generate_content_config=generate_content_config
    )
