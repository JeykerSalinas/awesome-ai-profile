import json
from typing import Literal

from langchain.tools import tool

from services.knowledge_service import get_profile_section_data, search_professional_experience


@tool
def get_candidate_photo() -> str:
    """Get Jeyker's professional profile photo."""
    return "/jeyker.jpg"


@tool
def get_profile_section(
    section: Literal["profile", "experience", "education", "skills", "projects"],
) -> str:
    """Get verified facts from a specific section of Jeyker's professional profile."""
    return json.dumps(get_profile_section_data(section), ensure_ascii=False)


@tool
def search_experience(query: str) -> str:
    """Search verified professional experience and projects using English or Spanish terms."""
    return json.dumps(search_professional_experience(query), ensure_ascii=False)
