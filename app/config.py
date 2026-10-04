"""Application configuration.

In Spring Boot this was `application.yml` + `@Value`. In FastAPI the idiomatic equivalent
is a pydantic-settings `BaseSettings` class: each attribute is read from an environment
variable (or a `.env` file) at startup, with a default value if it is not set.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed settings loaded from the environment / .env file.

    pydantic-settings matches each field to an environment variable of the SAME name in
    upper case (e.g. the field ``db_url`` is filled from ``DB_URL``).
    """

    # ---- Database (PostgreSQL + pgvector) ----
    db_url: str = "postgresql+psycopg://graminsahay:graminsahay@localhost:5432/graminsahay"

    # ---- LLM provider (OpenAI-compatible; override base_url for Groq) ----
    # Groq example:  openai_base_url=https://api.groq.com/openai/v1
    #                chat_model=llama-3.3-70b-versatile
    openai_api_key: str = "changeme"
    openai_base_url: str = "https://api.openai.com/v1"
    chat_model: str = "gpt-4o-mini"

    # ---- Embeddings (LOCAL — no API key needed) ----
    # all-MiniLM-L6-v2 produces 384-dimensional vectors and runs on CPU. This is the big win
    # of the Python stack: retrieval works offline, you only need an API key for explanations.
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384

    # ---- Speech-to-text (voice input) ----
    # Groq serves Whisper for transcription. whisper-large-v3-turbo is fast and multilingual
    # (handles English, Telugu and Hindi speech). Uses the same key/base_url as chat.
    transcribe_model: str = "whisper-large-v3-turbo"

    # ---- RAG retrieval knobs ----
    rag_top_k: int = 6
    rag_similarity_threshold: float = 0.3

    # ---- Knowledge base location ----
    schemes_path: str = "app/data/telangana_schemes.json"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton Settings instance.

    ``@lru_cache`` means the Settings object is built once and reused — the same idea as a
    Spring singleton bean. FastAPI dependencies call this to get configuration.
    """
    return Settings()
