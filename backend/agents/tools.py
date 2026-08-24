from langchain.tools import tool


@tool
def get_candidate_photo() -> str:
    """Get Jeyker's professional profile photo."""
    return "jeyker.jpg"