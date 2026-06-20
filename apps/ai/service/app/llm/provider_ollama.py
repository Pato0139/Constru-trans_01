import httpx
from typing import List, Dict, Any, Optional

from app.llm.base import BaseLLMProvider
from app.core.config import settings
from app.core.logging import logger


class OllamaProvider(BaseLLMProvider):
    name = "ollama"

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        logger.info(f"OllamaProvider initialized with model: {self.model}")

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        try:
            response = httpx.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=120.0
            )
            response.raise_for_status()
            result = response.json()
            return result["message"]["content"]
        except Exception as e:
            logger.error(f"Ollama chat error: {str(e)}")
            raise

    async def achat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                return result["message"]["content"]
        except Exception as e:
            logger.error(f"Ollama async chat error: {str(e)}")
            raise
