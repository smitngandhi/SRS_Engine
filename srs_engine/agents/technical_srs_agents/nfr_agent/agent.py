from google.adk.agents import LlmAgent
from .prompt import AGENT_DESCRIPTION , AGENT_INSTRUCTION
from ....schemas.technical_srs_schemas.nfr_schema import NonFunctionalRequirementsSection
from ....utils.globals import generate_content_config
from ....utils.model import *




## For app

def create_nfr_agent():
    return LlmAgent(
    name="nfr_agent",
    model=groq_llm,
    output_schema=NonFunctionalRequirementsSection,
    description=AGENT_DESCRIPTION,
    instruction=AGENT_INSTRUCTION,
    output_key="nfr_section",
    generate_content_config = generate_content_config
)
