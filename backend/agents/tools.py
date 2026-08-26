import json
from typing import Literal

from langchain.tools import tool

from services.knowledge_service import get_profile_section_data, search_professional_experience
from services.vector_store_service import get_vector_store_service


@tool
def offer_contact() -> str:
    """Offer two contact choices: public contact details or an editable demo email. Does not send anything."""
    return json.dumps({"contact_offer": True, "delivery": "simulation_only"})


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
