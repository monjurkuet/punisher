import httpx
from punisher.config import settings
import logging

logger = logging.getLogger("punisher.llm")


class LLMGateway:
    def __init__(self):
        self.base_url = settings.LLM_API_BASE
        self.model = settings.LLM_MODEL

    async def chat(self, messages: list[dict]) -> str:
        url = f"{self.base_url}/chat/completions"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    url,
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": 0.7,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"LLM Error: {e}")
            # Fallback mock for testing if server not running
            return (
                f"[LLM Error] Could not connect to {url}. Is the model server running?"
            )
