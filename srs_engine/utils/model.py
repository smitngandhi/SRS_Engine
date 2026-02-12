from dotenv import load_dotenv, find_dotenv
import os
from google.adk.models.lite_llm import LiteLlm

load_dotenv(find_dotenv())

GROQ_MODEL = os.getenv("GROQ_MODEL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE")
GROQ_MODEL_2 = os.getenv("GROQ_MODEL_2")


groq_llm = LiteLlm(
    model=GROQ_MODEL
)

ollama_llm = LiteLlm(
    model=OLLAMA_MODEL,
    api_base=OLLAMA_API_BASE
)

groq_llm_2 = LiteLlm(
    model = GROQ_MODEL_2,
)