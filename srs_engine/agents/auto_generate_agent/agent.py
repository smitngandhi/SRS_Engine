import os

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from srs_engine.schemas.glossary_schema import GlossarySection
from .prompt import CORE_FEATURES_AGENT_DESCRIPTION , CORE_FEATURES_AGENT_INSTRUCTION , PRIMARY_USER_FLOW_AGENT_DESCRIPTION , PRIMARY_USER_FLOW_AGENT_INSTRUCTION
from ...schemas.core_features_schema import CORE_FEATURES_Section
from ...schemas.primary_user_flow_schema import PRIMARY_USER_FLOW_Section
from ...utils.globals import generate_content_config
from ...utils.model import *



SECTION_SCHEMA_MAP = {
    "CORE_FEATURES": CORE_FEATURES_Section,
    "PRIMARY_USER_FLOW": PRIMARY_USER_FLOW_Section,
}



## For app

def create_auto_generate_agent(section: str):

    schema = SECTION_SCHEMA_MAP.get(section)
    return LlmAgent(
    name="auto_generate_agent",
    model=groq_llm_2,
    output_schema=schema,
    description=f"{section}_AGENT_DESCRIPTION",
    instruction=f"{section}_AGENT_INSTRUCTION",
    output_key=f"{section}_output",
    generate_content_config = generate_content_config
)
