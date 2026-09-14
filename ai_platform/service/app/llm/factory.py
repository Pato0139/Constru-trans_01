from app.core.config import settings
from app.llm.provider_openai_compatible import OpenAICompatibleProvider


def get_llm_provider():
    """
    Factory function to get the LLM provider based on settings.
    Supported provider: openai-compatible
    """
    if settings.LLM_PROVIDER == "openai":
        base_url = (
            settings.LLM_BASE_URL
            or settings.OPENAI_COMPAT_BASE_URL
            or "https://api.openai.com/v1"
        )
        api_key = settings.LLM_API_KEY or settings.OPENAI_COMPAT_API_KEY
        model = settings.LLM_MODEL or settings.OPENAI_COMPAT_MODEL or "gpt-4o-mini"
        return OpenAICompatibleProvider(
            base_url=base_url,
            api_key=api_key,
            model=model,
        )

    raise ValueError(
        f"Proveedor no soportado: {settings.LLM_PROVIDER}. Usa LLM_PROVIDER=openai."
    )
