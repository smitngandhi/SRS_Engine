from __future__ import annotations

import httpx
from typing import Any
from srs_engine.core.config import get_settings
from srs_engine.core.logging import get_logger

logger = get_logger(__name__)

class DiplomatService:
    """
    Handles AI-powered reframing of admin comments into polite user notifications.
    """
    def __init__(self, api_key: str | None = None):
        self.settings = get_settings()
        self.api_key = api_key or self.settings.groq_api_key
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"

    async def reframe_comment(self, action_type: str, raw_comment: str) -> str:
        """
        Uses Groq LLM to reframe a raw admin note into a professional email body.
        """
        if not self.api_key:
            logger.warning("DiplomatService | No API Key. Falling back to raw comment.")
            return raw_comment

        prompt = f"""
        You are 'The Diplomat', a professional communication assistant for SpecForge AI.
        An administrator has taken an action: {action_type}.
        The administrator's raw note is: "{raw_comment}"

        Your task is to reframe this note into a polite, professional, and clear email body for the user.
        - Maintain a helpful yet firm tone.
        - Do not use placeholders like [User Name].
        - Focus on the message content.
        - Keep it concise (2-3 paragraphs max).
        - Sign off as 'The SpecForge AI Team'.

        Polite Reframed Message:
        """

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": [
                            {"role": "system", "content": "You are a professional diplomat for a tech startup."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 500,
                    },
                )
                response.raise_for_status()
                data = response.json()
                reframed = data["choices"][0]["message"]["content"].strip()
                return reframed
        except Exception as e:
            logger.error(f"DiplomatService | AI Reframing failed: {e}")
            return f"Administrative Action Update: {raw_comment}"
