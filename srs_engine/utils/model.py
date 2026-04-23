from dotenv import load_dotenv, find_dotenv
import os
from google.adk.models.lite_llm import LiteLlm

load_dotenv(find_dotenv())

GROQ_MODEL = os.getenv("GROQ_MODEL")
GROQ_MODEL_2 = os.getenv("GROQ_MODEL_2")


groq_llm = LiteLlm(
    model=GROQ_MODEL
)

groq_llm_2 = LiteLlm(
    model = GROQ_MODEL_2,
)