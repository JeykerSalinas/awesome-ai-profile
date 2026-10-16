import json
from typing import Literal
from langchain.tools import tool
from services.profile_service import get_profile
from services.knowledge_service import get_profile_section_data, search_professional_experience
from services.public_contact import public_contact_details
from services.vector_store_service import get_vector_store_service

def build_search_documents_tool(document_ids: list[str] | None = None, profile_id: str = "jeyker"):
    """Bind profile and allowed document IDs outside the model's tool arguments."""
    get_profile(profile_id)
    allowed_document_ids = list(document_ids or [])

    @tool("search_documents")
    def search_documents(query: str) -> str:
        """Search the selected professional profile and PDFs attached to this conversation."""
        return json.dumps(get_vector_store_service(profile_id).search(query, allowed_document_ids), ensure_ascii=False)
    return search_documents

def build_profile_tools(profile_id: str = "jeyker"):
    """Create tools bound to one server-validated profile for text and voice."""
    profile = get_profile(profile_id)

    @tool
    def get_contact_details() -> str:
        """Get the selected candidate's authorized public contact details when requested."""
        return json.dumps(public_contact_details(profile.id), ensure_ascii=False)

    @tool
    def get_candidate_photo() -> str:
        """Get the selected candidate's professional photo, if available."""
        return profile.photo or "No verified professional photo is available."

    @tool
    def get_profile_section(section: Literal["profile", "experience", "education", "skills", "projects"]) -> str:
        """Get verified facts from a section of the selected professional profile."""
        return json.dumps(get_profile_section_data(section, profile.id), ensure_ascii=False)

    @tool
    def search_experience(query: str) -> str:
        """Search verified professional experience and projects in English or Spanish."""
        return json.dumps(search_professional_experience(query, profile_id=profile.id), ensure_ascii=False)

    tools = [get_contact_details, get_profile_section, search_experience]
    if profile.photo:
        tools.append(get_candidate_photo)
    return [item for item in tools if profile.tool_enabled(item.name)]

# Compatibility exports for callers using the original default profile.
_default_tools = {item.name: item for item in build_profile_tools()}
get_contact_details = _default_tools.get("get_contact_details")
get_candidate_photo = _default_tools.get("get_candidate_photo")
get_profile_section = _default_tools.get("get_profile_section")
search_experience = _default_tools.get("search_experience")


def build_agent_tools(document_ids=None, profile_id="jeyker"):
    profile = get_profile(profile_id)
    tools = build_profile_tools(profile_id)
    if profile.tool_enabled("search_documents"):
        tools.append(build_search_documents_tool(document_ids if profile.public.features.documents else [], profile_id))
    return tools
