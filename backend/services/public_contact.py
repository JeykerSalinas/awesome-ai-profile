"""Public contact details Jeyker has authorized the assistant to share."""


def public_contact_details(profile_id: str = "jeyker") -> dict[str, str]:
    from services.profile_service import get_profile
    if get_profile(profile_id).id != "jeyker":
        return {}
    return {
        "phone": "+34 624 179 342",
        "email": "jeyker.salinas13@gmail.com",
        "github": "https://github.com/JeykerSalinas",
        "linkedin": "https://www.linkedin.com/in/jeyker-salinas-608486158/",
    }
