import httpx
from punisher.config import settings
import logging
import asyncio

logger = logging.getLogger("punisher.llm")


class LLMGateway:
    def __init__(self):
        # Ordered list of endpoints to try
        self.endpoints = [
            settings.LLM_API_BASE,
            settings.OLLAMA_API_BASE,
        ]
        # Ordered list of models to try
        self.models = [
            settings.LLM_MODEL,  # Primary model from config (vision-model_QWEN)
            "vision-model_QWEN",  # Specific fallback
            "llama3",  # Common Ollama fallback
            "mistral",  # Common Ollama fallback
            "phi3",  # Small fallback
        ]

    async def chat(self, messages: list[dict]) -> str:
        """
        Robust chat completion with aggressive failover across endpoints and models.
        It will keep trying combinations until a success occurs or all options are exhausted.
        """
        last_error = "Unknown error"

        # We loop through endpoints first, then models.
        # This is because an endpoint might be up but missing a specific model.
        for endpoint in self.endpoints:
            if not endpoint:
                continue

            for model in self.models:
                if not model:
                    continue

                attempts = 0
                max_retries = 2

                while attempts < max_retries:
                    try:
                        logger.info(
                            f"LLM Attempt: endpoint={endpoint}, model={model}, attempt={attempts + 1}"
                        )
                        response = await self._send_request(endpoint, model, messages)
                        return response
                    except httpx.ConnectError:
                        logger.warning(
                            f"Connection Refused: {endpoint}. Skipping endpoint."
                        )
                        # If connection is refused, don't bother trying other models on this endpoint
                        break
                    except Exception as e:
                        attempts += 1
                        last_error = str(e)
                        logger.warning(f"LLM Error ({model} @ {endpoint}): {e}")
                        if attempts < max_retries:
                            await asyncio.sleep(0.5)  # Short wait before retry
                        else:
                            continue  # Move to next model

        return f"[FATAL ERROR] All neural pathways severed. Check local model servers (127.0.0.1:8087 or 11434).\nLast error: {last_error}"

    async def _send_request(
        self, base_url: str, model: str, messages: list[dict]
    ) -> str:
        url = f"{base_url}/chat/completions"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0.7,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
