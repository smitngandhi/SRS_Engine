from google.adk.agents import LlmAgent
from .prompt import AGENT_DESCRIPTION , AGENT_INSTRUCTION
from ....schemas.technical_srs_schemas.system_features_schema import SystemFeaturesSection
from ....utils.globals import generate_content_config
from ....utils.model import *




## For app

def create_system_features_agent():
    return LlmAgent(
    name="system_features_agent",
    model=groq_llm,
    output_schema=SystemFeaturesSection,
    description=AGENT_DESCRIPTION,
    instruction=AGENT_INSTRUCTION,
    output_key="system_features_section",
    generate_content_config = generate_content_config
)