from app.core.config import settings
from app.llm.provider_ollama import OllamaProvider
from app.llm.provider_openai_compatible import OpenAICompatibleProvider


def get_llm_provider():
    """
    Factory function to get the LLM provider based on settings.
    Supported providers: ollama, openai
    """
    if settings.LLM_PROVIDER == "ollama":
        return OllamaProvider()

    if settings.LLM_PROVIDER == "openai":
        return OpenAICompatibleProvider(
            base_url=settings.OPENAI_COMPAT_BASE_URL,
            api_key=settings.OPENAI_COMPAT_API_KEY,
            model=settings.OPENAI_COMPAT_MODEL,
        )

    raise ValueError(f"Proveedor no soportado: {settings.LLM_PROVIDER}")
