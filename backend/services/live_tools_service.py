from __future__ import annotations

import asyncio
import logging
from typing import Any

from google.genai import types
from langchain_core.tools import BaseTool

from agents.tools import (
    build_search_documents_tool,
    get_candidate_photo,
    get_profile_section,
    search_experience,
)


logger = logging.getLogger(__name__)


def build_live_tools(document_ids: list[str] | None = None) -> dict[str, BaseTool]:
    tools = [
        get_candidate_photo,
        get_profile_section,
        search_experience,
        build_search_documents_tool(document_ids),
    ]
    return {tool.name: tool for tool in tools}


def build_live_tool_config(tools: dict[str, BaseTool]) -> types.Tool:
    declarations = []
    for tool in tools.values():
        schema = tool.args_schema.model_json_schema() if tool.args_schema else {"type": "object"}
        declarations.append(
            types.FunctionDeclaration(
                name=tool.name,
                description=tool.description,
                parameters_json_schema=schema,
            )
        )
    return types.Tool(function_declarations=declarations)


async def execute_live_tool(tool: BaseTool, arguments: dict[str, Any] | None) -> Any:
    try:
        return await asyncio.to_thread(tool.invoke, arguments or {})
    except Exception:
        logger.exception("Gemini Live tool '%s' failed", tool.name)
        return {"error": "The requested tool could not be completed."}
