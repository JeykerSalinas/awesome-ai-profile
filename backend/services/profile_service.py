"""Server-owned profiles. Never resolve filesystem paths from client input."""
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ProfileId = Literal["jeyker", "sara"]
BACKEND_ROOT = Path(__file__).resolve().parent.parent

@dataclass(frozen=True)
class ProfessionalProfile:
    id: ProfileId
    assistant_name: str
    candidate_name: str
    knowledge_root: Path
    photo: str | None = None

PROFILES = {
    "jeyker": ProfessionalProfile("jeyker", "Django", "Jeyker Salinas", BACKEND_ROOT / "knowledge", "/jeyker.jpg"),
    "sara": ProfessionalProfile("sara", "Sara", "Sara", BACKEND_ROOT / "profiles" / "sara" / "knowledge"),
}

def get_profile(profile_id: str = "jeyker") -> ProfessionalProfile:
    if profile_id not in PROFILES:
        raise ValueError("Unknown professional profile.")
    return PROFILES[profile_id]

def initial_greeting(locale: str, profile_id: str = "jeyker") -> str:
    profile = get_profile(profile_id)
    if locale == "es":
        return f"Hola, soy {profile.assistant_name}, asistente profesional de {profile.candidate_name}."
    return f"Hi, I'm {profile.assistant_name}, {profile.candidate_name}'s professional assistant."
