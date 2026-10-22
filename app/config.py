"""Application configuration.

In Spring Boot this was `application.yml` + `@Value`. In FastAPI the idiomatic equivalent
is a pydantic-settings `BaseSettings` class: each attribute is read from an environment
variable (or a `.env` file) at startup, with a default value if it is not set.
"""

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed settings loaded from the environment / .env file.

    pydantic-settings matches each field to an environment variable of the SAME name in
    upper case (e.g. the field ``db_url`` is filled from ``DB_URL``).
    """

    # ---- Database (PostgreSQL + pgvector) ----
    # Reads DB_URL locally; also accepts DATABASE_URL (what Railway/Render/Heroku inject).
    db_url: str = Field(
        default="postgresql+psycopg://graminsahay:graminsahay@localhost:5432/graminsahay",
        validation_alias=AliasChoices("DB_URL", "DATABASE_URL"),
    )

    # ---- LLM provider (OpenAI-compatible; override base_url for Groq) ----
    # Groq example:  openai_base_url=https://api.groq.com/openai/v1
    #                chat_model=llama-3.3-70b-versatile
    openai_api_key: str = "changeme"
    openai_base_url: str = "https://api.openai.com/v1"
    chat_model: str = "gpt-4o-mini"

    # ---- Embeddings (LOCAL — no API key needed) ----
    # all-MiniLM-L6-v2 produces 384-dimensional vectors and runs on CPU. This is the big win
    # of the Python stack: retrieval works offline, you only need an API key for explanations.
    # It runs via fastembed (ONNX Runtime, no PyTorch), so the app fits in ~512 MB RAM.
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384
    # Where the downloaded model files are kept. Kept inside the project (and git-ignored) so a
    # model downloaded during the cloud build is still there when the server starts.
    embedding_cache_dir: str = ".cache/fastembed"

    # ---- Speech-to-text (voice input) ----
    # Groq serves Whisper for transcription. whisper-large-v3-turbo is fast and multilingual
    # (handles English, Telugu and Hindi speech). Uses the same key/base_url as chat.
    transcribe_model: str = "whisper-large-v3-turbo"

    # ---- RAG retrieval knobs ----
    rag_top_k: int = 6
    rag_similarity_threshold: float = 0.3

    # ---- Knowledge base location ----
    schemes_path: str = "app/data/telangana_schemes.json"

    # ---- Authentication (JWT) ----
    # IMPORTANT: set a strong, random JWT_SECRET in production (env var). The default is only
    # for local development. Generate one with:  python -c "import secrets; print(secrets.token_hex(32))"
    jwt_secret: str = "dev-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # tokens valid for 24 hours

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def sqlalchemy_url(self) -> str:
        """Normalise the DB URL so SQLAlchemy always uses the psycopg (v3) driver.

        Cloud platforms (Railway, Render, Heroku) inject a DATABASE_URL that begins with
        'postgres://' or 'postgresql://'. SQLAlchemy needs the explicit driver
        'postgresql+psycopg://'. We rewrite the scheme here so the same code runs locally
        (docker-compose) and in the cloud with no changes.
        """
        url = self.db_url
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://") :]
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://") :]
        return url


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton Settings instance.

    ``@lru_cache`` means the Settings object is built once and reused — the same idea as a
    Spring singleton bean. FastAPI dependencies call this to get configuration.
    """
    return Settings()
