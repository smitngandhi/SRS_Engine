from google.adk.agents import LlmAgent
from .prompt import AGENT_DESCRIPTION , AGENT_INSTRUCTION
from ....schemas.home_page_schemas.problem_statement_enhance_schema import EnhancedProblemStatementSection
from ....utils.globals import generate_content_config
from ....utils.model import *






from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LLMResponse
def validate_output(schema_class):
    """Returns a callback that parses + validates the raw JSON text response."""
    def _callback(callback_context: CallbackContext, llm_response: LLMResponse):
        for part in llm_response.content.parts:
            if part.text:
                try:
                    # Strip markdown fences if the model adds them
                    text = part.text.strip().removeprefix("```json").removesuffix("```").strip()
                    validated = schema_class.model_validate_json(text)
                    # Write validated output into session state manually
                    callback_context.state[callback_context.agent_name + "_output"] = validated.model_dump()
                except Exception as e:
                    # Log and let ADK handle as a normal text response
                    print(f"[validate_output] Schema validation failed: {e}")
        return None  # Don't replace the response, just side-effect state

    return _callback
## For app

def create_enhance_problem_statement_agent():
    return LlmAgent(
    name="enhance_problem_statement_agent",
    model=groq_llm_2,
    # output_schema=EnhancedProblemStatementSection,
    after_agent_callback=validate_output(EnhancedProblemStatementSection),
    description=AGENT_DESCRIPTION,
    instruction=AGENT_INSTRUCTION,
    output_key=f"enhanced_problem_statement_output",
    generate_content_config = generate_content_config
)
