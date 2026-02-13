from google.adk.agents import LlmAgent
from .prompt import AGENT_DESCRIPTION , AGENT_INSTRUCTION
from ....schemas.technical_srs_schemas.overall_description_schema import OverallDescriptionSection
from ....utils.globals import generate_content_config
from ....utils.model import *




## For app

def create_overall_description_agent():
    return LlmAgent(
        name="overall_description_agent",
        model=groq_llm,
        output_schema=OverallDescriptionSection,
        description=AGENT_DESCRIPTION,
        instruction=AGENT_INSTRUCTION,
        output_key="overall_description_section",
        generate_content_config= generate_content_config
    )
