import json
from typing import Literal

from langchain.tools import tool

from services.knowledge_service import get_profile_section_data, search_professional_experience
from services.vector_store_service import get_vector_store_service
from services.public_contact import public_contact_details
from settings import get_settings


@tool
def offer_contact() -> str:
    """Offer contact only after genuine hiring/interview interest or an explicit contact request. Wait for the visitor to choose. Does not open a form or send anything."""
    return json.dumps({"contact_offer": True, "delivery": get_settings().contact_delivery_mode})


@tool
def get_contact_details() -> str:
    """Read Jeyker's authorized public phone, email, GitHub and LinkedIn after the visitor chooses contact details. Present them in your normal answer with links."""
    return json.dumps(public_contact_details(), ensure_ascii=False)


@tool
def open_contact_form() -> str:
    """Embed an editable email form after the visitor chooses to write. The form displays the configured delivery mode. This tool does NOT send or approve an email."""
    return json.dumps({"contact_form": True, "delivery": get_settings().contact_delivery_mode})


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


def build_search_documents_tool(document_ids: list[str] | None = None):
    """Bind the current request's allowed document IDs to the retrieval tool."""
    allowed_document_ids = list(document_ids or [])

    @tool("search_documents")
    def search_documents(query: str) -> str:
        """Semantically search verified profile knowledge and PDFs uploaded in this chat. Use this before comparing Jeyker with a CV, letter, or job offer."""
        results = get_vector_store_service().search(query, allowed_document_ids)
        return json.dumps(results, ensure_ascii=False)

    return search_documents
