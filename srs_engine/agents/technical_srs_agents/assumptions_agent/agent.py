from google.adk.agents import LlmAgent
from .prompt import AGENT_DESCRIPTION , AGENT_INSTRUCTION
from ....schemas.technical_srs_schemas.assumptions_schema import AssumptionsSection
from ....utils.globals import generate_content_config
from ....utils.model import *




## For app

def create_assumptions_agent():
    return LlmAgent(
    name="assumptions_agent",
    model=groq_llm,
    output_schema=AssumptionsSection,
    description=AGENT_DESCRIPTION,
    instruction=AGENT_INSTRUCTION,
    output_key="assumptions_section",
    generate_content_config = generate_content_config
)
