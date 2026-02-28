from google.adk.agents import LlmAgent
from ....core.logging import get_context_logger
from .prompt import AGENT_DESCRIPTION, AGENT_INSTRUCTION
from ....schemas.technical_srs_schemas.introduction_schema import IntroductionSection
from ....utils.globals import generate_content_config
from ....utils.model import *

logger = get_context_logger(__name__)


def create_introduction_agent():
    """Create Introduction section agent with logging."""
    logger.debug("create_introduction_agent | Initializing Introduction Agent")
    
    agent = LlmAgent(
        name="introduction_agent",
        model=groq_llm,
        output_schema=IntroductionSection,
        description=AGENT_DESCRIPTION,
        instruction=AGENT_INSTRUCTION,
        output_key="introduction_section",
        generate_content_config=generate_content_config
    )
    
    logger.debug("create_introduction_agent | Introduction Agent created successfully")
    return agent
