import os

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from srs_engine.schemas.glossary_schema import GlossarySection
from .prompt import AGENT_DESCRIPTION , AGENT_INSTRUCTION
from ...schemas.problem_statement_enhance_schema import EnhancedProblemStatementSection
from ...utils.globals import generate_content_config
from ...utils.model import *







## For app

def create_enhance_problem_statement_agent():
    return LlmAgent(
    name="enhance_problem_statement_agent",
    model=groq_llm_2,
    output_schema=EnhancedProblemStatementSection,
    description=AGENT_DESCRIPTION,
    instruction=AGENT_INSTRUCTION,
    output_key=f"enhanced_problem_statement_output",
    generate_content_config = generate_content_config
)
