"""Validated server-owned configuration; only public.json is bundled by Vite."""
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

ProfileId = Literal["jeyker", "sara"]
BACKEND_ROOT = Path(__file__).resolve().parent.parent
PROFILE_IDS = ("jeyker", "sara")
ToolName = Literal["get_contact_details", "get_candidate_photo", "get_profile_section", "search_experience", "search_documents"]

class ConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

class Features(ConfigModel):
    voice: bool
    documents: bool
    tools: bool
    tour: bool

class Analytics(ConfigModel):
    enabled: bool
    projectToken: str | None = None
    host: str | None = None

class PublicProfile(ConfigModel):
    id: ProfileId
    assistantName: str = Field(min_length=1)
    candidateName: str = Field(min_length=1)
    logo: str | None
    avatar: str | None
    avatarDark: str | None
    colors: dict[str, str]
    texts: dict[Literal["en", "es"], dict[str, str]]
    features: Features
    analytics: Analytics
    apiBaseUrl: str | None = None

class Services(ConfigModel):
    google_api_key_env: str | None = Field(default=None, pattern=r"^[A-Z][A-Z0-9_]*$")
    vector_store_path: str | None = None
    chat_model: str = Field(min_length=1)
    embedding_model: str | None = None
    live_model: str | None = None
    live_voice: str | None = None

class AgentProfile(ConfigModel):
    candidate_name: str = Field(min_length=1)
    knowledge_path: str
    photo: str | None = None
    contact: dict[str, str] = Field(default_factory=dict)
    instructions: str = ""
    allowed_tools: list[ToolName]
    services: Services

class ProfessionalProfile(ConfigModel):
    id: ProfileId
    assistant_name: str
    candidate_name: str
    knowledge_root: Path
    photo: str | None
    public: PublicProfile
    agent: AgentProfile

    def tool_enabled(self, name: str) -> bool:
        return self.public.features.tools and name in self.agent.allowed_tools

def merge_config(defaults: dict, overrides: dict) -> dict:
    """Objects merge recursively; scalars, nulls and lists replace defaults."""
    result = dict(defaults)
    for key, value in overrides.items():
        result[key] = merge_config(result[key], value) if isinstance(value, dict) and isinstance(result.get(key), dict) else value
    return result

@lru_cache(maxsize=2)
def get_profile(profile_id: str = "jeyker") -> ProfessionalProfile:
    if profile_id not in PROFILE_IDS:
        raise ValueError("Unknown professional profile.")
    root = BACKEND_ROOT / "profiles"
    def load(kind):
        return merge_config(json.loads((root / "defaults" / f"{kind}.json").read_text()), json.loads((root / profile_id / f"{kind}.json").read_text()))
    public = PublicProfile.model_validate(load("public"))
    agent = AgentProfile.model_validate(load("agent"))
    if public.id != profile_id:
        raise ValueError("Profile ID does not match its directory.")
    knowledge = (BACKEND_ROOT / agent.knowledge_path).resolve()
    if not knowledge.is_relative_to(BACKEND_ROOT) or not knowledge.is_dir():
        raise ValueError("Knowledge must be an existing directory within the backend.")
    return ProfessionalProfile(id=profile_id, assistant_name=public.assistantName,
        candidate_name=agent.candidate_name, knowledge_root=knowledge,
        photo=agent.photo, public=public, agent=agent)

def profile_settings(profile_id, settings):
    """Resolve secrets on the server. Explicit key references never fall back."""
    services = get_profile(profile_id).agent.services
    updates = {}
    if services.google_api_key_env:
        key = os.environ.get(services.google_api_key_env)
        if not key:
            raise ValueError("The profile's configured API key is missing.")
        updates["google_api_key"] = key
    for source, target in [("vector_store_path", "vector_store_path"), ("embedding_model", "embedding_model"), ("live_model", "gemini_live_model"), ("live_voice", "gemini_live_voice")]:
        value = getattr(services, source)
        if value is not None:
            updates[target] = value
    return settings.model_copy(update=updates) if updates else settings

def require_feature(profile_id: str, feature: str) -> None:
    from fastapi import HTTPException
    if not getattr(get_profile(profile_id).public.features, feature):
        raise HTTPException(status_code=403, detail=f"{feature} is disabled for this profile.")

def initial_greeting(locale: str, profile_id: str = "jeyker") -> str:
    profile = get_profile(profile_id)
    name = profile.public.candidateName
    if locale == "es":
        return f"Hola, soy {profile.assistant_name}, asistente profesional de {name}."
    return f"Hi, I'm {profile.assistant_name}, {name}'s professional assistant."

# Fail early for invalid checked-in configuration, rather than during a request.
for _id in PROFILE_IDS:
    get_profile(_id)
