from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    backend_host: str = Field(
        default="127.0.0.1",
        validation_alias=AliasChoices("BACKEND_HOST"),
    )
    backend_port: int = Field(
        default=8000,
        validation_alias=AliasChoices("BACKEND_PORT"),
    )
    cors_allow_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        validation_alias=AliasChoices("CORS_ALLOW_ORIGINS"),
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_allow_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allow_origins.split(",")
            if origin.strip()
        ]

    google_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_API_KEY"),
    )
    database_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL"),
    )
    vector_store_path: str = Field(default="data/chroma", validation_alias=AliasChoices("VECTOR_STORE_PATH"))
    embedding_model: str = Field(default="models/gemini-embedding-001", validation_alias=AliasChoices("EMBEDDING_MODEL"))
    rag_chunk_size: int = Field(default=900, validation_alias=AliasChoices("RAG_CHUNK_SIZE"))
    rag_chunk_overlap: int = Field(default=150, validation_alias=AliasChoices("RAG_CHUNK_OVERLAP"))
    rag_result_limit: int = Field(default=5, validation_alias=AliasChoices("RAG_RESULT_LIMIT"))
    max_pdf_size_mb: int = Field(default=10, validation_alias=AliasChoices("MAX_PDF_SIZE_MB"))
    upload_ttl_minutes: int = Field(default=30, validation_alias=AliasChoices("UPLOAD_TTL_MINUTES"))
    contact_delivery_mode: Literal["simulation", "resend"] = "simulation"
    contact_email_enabled: bool = False
    resend_api_key: SecretStr | None = None
    contact_from_email: str = ""
    # Accepted only for compatibility with earlier .env files; ignored by contact.
    contact_database_url: SecretStr | None = Field(default=None, exclude=True, repr=False)
    contact_daily_limit: int = Field(default=20, ge=1, le=1000)
    contact_sessions_per_hour: int = Field(default=60, ge=1, le=10000)
    contact_max_sessions: int = Field(default=10000, ge=1, le=100000)


@lru_cache
def get_settings() -> Settings:
    return Settings()
