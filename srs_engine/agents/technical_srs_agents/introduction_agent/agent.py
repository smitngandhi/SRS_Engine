from google.adk.agents import LlmAgent
from .prompt import AGENT_DESCRIPTION , AGENT_INSTRUCTION
from ....schemas.technical_srs_schemas.introduction_schema import IntroductionSection
from ....utils.globals import generate_content_config
from ....utils.model import *



## For app

def create_introduction_agent():
    return LlmAgent(
    name="introduction_agent",
    model=groq_llm,
    output_schema=IntroductionSection,
    description=AGENT_DESCRIPTION,
    instruction=AGENT_INSTRUCTION,
    output_key="introduction_section",
    generate_content_config = generate_content_config
)
