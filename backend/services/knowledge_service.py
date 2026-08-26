from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Literal


KnowledgeSection = Literal["profile", "experience", "education", "skills", "projects"]

KNOWLEDGE_ROOT = Path(__file__).resolve().parent.parent / "knowledge"
SECTION_FILES: dict[str, str] = {
    "profile": "profile.json",
    "experience": "experience.json",
    "education": "education.json",
    "skills": "skills.json",
    "projects": "projects/index.json",
}

SPANISH_SEARCH_ALIASES: dict[str, tuple[str, ...]] = {
    "agente": ("agent",),
    "agentes": ("agents", "agent"),
    "aprendizaje": ("learning",),
    "artificial": ("artificial",),
    "aumentada": ("augmented", "rag"),
    "aumentado": ("augmented", "rag"),
    "busqueda": ("retrieval", "search"),
    "datos": ("data",),
    "desarrollador": ("developer", "development"),
    "desarrollo": ("development", "developer"),
    "educacion": ("education", "educational"),
    "educativa": ("educational", "education"),
    "educativo": ("educational", "education"),
    "experiencia": ("experience",),
    "formacion": ("education",),
    "generacion": ("generation", "rag"),
    "habilidades": ("skills",),
    "herramientas": ("tools",),
    "historia": ("history",),
    "ingeniero": ("engineer", "engineering"),
    "inteligencia": ("intelligence",),
    "lenguajes": ("languages",),
    "maestria": ("master",),
    "medica": ("medical",),
    "medicina": ("medical",),
    "monitoreo": ("monitoring",),
    "plataforma": ("platform",),
    "practicas": ("intern", "internship"),
    "proyecto": ("project",),
    "proyectos": ("projects", "project"),
    "recuperacion": ("retrieval", "rag"),
    "salud": ("medical", "health"),
    "tableros": ("dashboards",),
    "tecnologias": ("technologies",),
    "universidad": ("university", "universidad"),
    "vectoriales": ("vector",),
    "visualizacion": ("visualization",),
}

STOP_WORDS = {
    "a", "an", "and", "con", "de", "del", "el", "en", "for", "has",
    "his", "in", "jeyker", "la", "las", "los", "of", "on", "que", "su",
    "the", "what", "with", "y",
}


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(character for character in normalized if not unicodedata.combining(character))


def _query_terms(query: str) -> set[str]:
    words = set(re.findall(r"[a-z0-9]+", _normalize(query))) - STOP_WORDS
    expanded = set(words)

    for word in words:
        expanded.update(SPANISH_SEARCH_ALIASES.get(word, ()))

    return expanded


@lru_cache(maxsize=None)
def _load_json(relative_path: str) -> dict[str, object]:
    path = (KNOWLEDGE_ROOT / relative_path).resolve()

    if not path.is_relative_to(KNOWLEDGE_ROOT):
        raise ValueError("Knowledge paths must stay inside the knowledge directory.")

    return json.loads(path.read_text(encoding="utf-8"))


def get_profile_section_data(section: str) -> dict[str, object]:
    relative_path = SECTION_FILES.get(section)

    if relative_path is None:
        supported = ", ".join(SECTION_FILES)
        raise ValueError(f"Unknown knowledge section '{section}'. Supported sections: {supported}.")

    return {
        "section": section,
        "source": f"knowledge/{relative_path}",
        "data": _load_json(relative_path),
    }


def _project_document(relative_path: str) -> str:
    path = (KNOWLEDGE_ROOT / relative_path).resolve()

    if not path.is_relative_to(KNOWLEDGE_ROOT):
        raise ValueError("Project documents must stay inside the knowledge directory.")

    return path.read_text(encoding="utf-8")


def _score_candidate(candidate: dict[str, object], terms: set[str]) -> int:
    title = _normalize(str(candidate.get("title", "")))
    technologies = _normalize(" ".join(str(item) for item in candidate.get("technologies", [])))
    content = _normalize(str(candidate.get("content", "")))
    score = 0

    for term in terms:
        if len(term) < 2:
            continue
        if term in title:
            score += 5
        if term in technologies:
            score += 4
        if term in content:
            score += 1

    return score


def search_professional_experience(query: str, limit: int = 4) -> dict[str, object]:
    terms = _query_terms(query)

    if not terms:
        return {"query": query, "results": [], "count": 0}

    experience = get_profile_section_data("experience")["data"]
    projects = get_profile_section_data("projects")["data"]
    candidates: list[dict[str, object]] = []

    for position in experience["positions"]:
        candidates.append(
            {
                "kind": "experience",
                "id": position["id"],
                "title": position["role"],
                "organization": position["organization"],
                "period": f"{position['start_date']} to {position['end_date']}",
                "summary": position["summary"],
                "technologies": position["technologies"],
                "source": "knowledge/experience.json",
                "content": " ".join(
                    [
                        position["role"],
                        position["organization"],
                        position["summary"],
                        *position["responsibilities"],
                    ]
                ),
            }
        )

    for project in projects["projects"]:
        candidates.append(
            {
                "kind": "project",
                "id": project["id"],
                "title": project["title"],
                "organization": project["organization"],
                "summary": project["summary"],
                "technologies": project["technologies"],
                "source": f"knowledge/{project['document']}",
                "content": _project_document(project["document"]),
            }
        )

    scored = sorted(
        (
            (score, candidate)
            for candidate in candidates
            if (score := _score_candidate(candidate, terms)) > 0
        ),
        key=lambda item: item[0],
        reverse=True,
    )

    results = []
    for score, candidate in scored[: max(1, min(limit, 10))]:
        result = {key: value for key, value in candidate.items() if key != "content"}
        result["score"] = score
        results.append(result)

    return {"query": query, "results": results, "count": len(results)}
