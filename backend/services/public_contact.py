"""Only explicitly configured public contact details can be returned by tools."""
from services.profile_service import get_profile

def public_contact_details(profile_id: str = "jeyker") -> dict[str, str]:
    return dict(get_profile(profile_id).agent.contact)
