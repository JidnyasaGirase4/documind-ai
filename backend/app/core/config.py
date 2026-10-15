"""Application settings, loaded from environment variables / the backend `.env` file."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]

_PLACEHOLDER_SECRETS = {"", "replace_with_a_long_random_secret", "changeme", "secret"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "DocuMind AI API"
    app_env: str = "development"  # development | test | production
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    # One origin, or several separated by commas.
    frontend_origin: str = "http://localhost:5173"

    # Required: there is deliberately no default so credentials never live in the code.
    database_url: str = Field(..., description="e.g. mysql+pymysql://root:PASSWORD@127.0.0.1:3306/documind_ai?charset=utf8mb4")

    jwt_secret_key: str = Field(..., description="Long random secret used to sign access tokens")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    # LLM: anthropic | openai | mock (mock is development-only and clearly labelled)
    llm_provider: str = "mock"
    llm_api_key: str = ""
    llm_model: str = ""
    llm_base_url: str = ""  # only used by the openai-compatible provider
    llm_timeout_seconds: float = 60.0
    llm_max_tokens: int = 1024
    # Low randomness keeps answers close to the sources.
    llm_temperature: float = 0.1
    llm_frequency_penalty: float = 0.0  # set ~0.3 for small local models that repeat themselves

    # Embeddings: sentence_transformers | hashing (hashing is a tiny deterministic dev/test embedder)
    embedding_provider: str = "sentence_transformers"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    chroma_persist_directory: str = "./data/chroma"
    upload_directory: str = "./data/uploads"
    max_upload_size_mb: int = 20
    chunk_size: int = 800
    chunk_overlap: int = 120
    top_k_results: int = 5
    # Only a floor that drops completely unrelated chunks. Short questions score low against long chunks, so a
    # high cutoff rejects valid questions; the LLM decides whether the passages really answer (INSUFFICIENT_EVIDENCE).
    retrieval_min_similarity: float = 0.05

    rate_limit_enabled: bool = True

    @model_validator(mode="after")
    def _validate(self) -> "Settings":
        if self.app_env == "production":
            problems = []
            if self.jwt_secret_key in _PLACEHOLDER_SECRETS or len(self.jwt_secret_key) < 32:
                problems.append("JWT_SECRET_KEY must be a random value of at least 32 characters")
            if self.llm_provider == "mock":
                problems.append("LLM_PROVIDER=mock is development-only and cannot be used in production")
            if self.embedding_provider == "hashing":
                problems.append("EMBEDDING_PROVIDER=hashing is development/test-only")
            if not self.frontend_origin or "*" in self.frontend_origin:
                problems.append("FRONTEND_ORIGIN must list the real frontend origin(s), not '*'")
            if problems:
                raise ValueError("Invalid production configuration: " + "; ".join(problems))
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.frontend_origin.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    def resolve_path(self, value: str) -> Path:
        """Relative paths are resolved against the backend directory."""
        p = Path(value)
        return p if p.is_absolute() else (BACKEND_DIR / p).resolve()

    @property
    def upload_path(self) -> Path:
        return self.resolve_path(self.upload_directory)

    @property
    def chroma_path(self) -> Path:
        return self.resolve_path(self.chroma_persist_directory)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
