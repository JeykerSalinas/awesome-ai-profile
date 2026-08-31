from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices("LOG_LEVEL"),
    )
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
    gemini_live_model: str = Field(
        default="gemini-3.1-flash-live-preview",
        validation_alias=AliasChoices("GEMINI_LIVE_MODEL"),
    )
    gemini_live_voice: str = Field(
        default="Kore",
        validation_alias=AliasChoices("GEMINI_LIVE_VOICE"),
    )
    gemini_live_max_turns: int = Field(
        default=20,
        ge=1,
        le=100,
        validation_alias=AliasChoices("GEMINI_LIVE_MAX_TURNS"),
    )
    channel_default_locale: Literal["en", "es"] = Field(
        default="es",
        validation_alias=AliasChoices("CHANNEL_DEFAULT_LOCALE"),
    )
    channel_public_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("CHANNEL_PUBLIC_BASE_URL"),
    )
    whatsapp_verify_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("WHATSAPP_VERIFY_TOKEN"),
    )
    whatsapp_app_secret: str | None = Field(
        default=None,
        validation_alias=AliasChoices("WHATSAPP_APP_SECRET"),
    )
    whatsapp_access_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("WHATSAPP_ACCESS_TOKEN"),
    )
    whatsapp_phone_number_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("WHATSAPP_PHONE_NUMBER_ID"),
    )
    meta_graph_api_version: str = Field(
        default="v26.0",
        validation_alias=AliasChoices("META_GRAPH_API_VERSION"),
    )
    twilio_auth_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("TWILIO_AUTH_TOKEN"),
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
