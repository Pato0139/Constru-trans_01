from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AI Service"
    DEBUG: bool = True

    # Database Settings
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "constru_trans_ai"

    # Redis Settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # ChromaDB Settings
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000

    # LLM Settings
    LLM_PROVIDER: str = "ollama"  # ollama, openai, llamacpp, vllm

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:latest"

    # OpenAI-compatible
    OPENAI_COMPAT_BASE_URL: str = "http://localhost:8000/v1"
    OPENAI_COMPAT_API_KEY: str = "local-key"
    OPENAI_COMPAT_MODEL: str = "llama3.2:latest"

    # Embeddings Settings
    EMBEDDINGS_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Security Settings
    AI_INTERNAL_TOKEN: str = "super-internal-token"

    # File Upload Settings
    UPLOAD_DIR: str = "../../data/uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
