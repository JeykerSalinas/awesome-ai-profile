from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from pydantic import BaseModel

from schemas.events import DoneEvent, ErrorData, ErrorEvent, MessageDeltaData, MessageDeltaEvent


MODEL_ORDER: list[type[BaseModel]] = [
    MessageDeltaData,
    MessageDeltaEvent,
    DoneEvent,
    ErrorData,
    ErrorEvent,
]

UNION_NAME = "StreamEvent"
UNION_MEMBERS = ["MessageDeltaEvent", "DoneEvent", "ErrorEvent"]


def render_type(schema: dict[str, Any], defs: dict[str, Any]) -> str:
    if "$ref" in schema:
        return schema["$ref"].split("/")[-1]

    schema_type = schema.get("type")

    if "const" in schema:
        return f'"{schema["const"]}"'

    if "enum" in schema:
        return " | ".join(f'"{item}"' for item in schema["enum"])

    if schema_type == "string":
        return "string"

    if schema_type == "integer" or schema_type == "number":
        return "number"

    if schema_type == "boolean":
        return "boolean"

    if schema_type == "null":
        return "null"

    if schema_type == "array":
        return f"{render_type(schema['items'], defs)}[]"

    if schema_type == "object":
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))
        additional = schema.get("additionalProperties")

        if not properties and (additional is None or additional is False or additional is True):
            return "{}"

        lines = ["{"]
        for key, value in properties.items():
            optional = "?" if key not in required else ""
            lines.append(f"  {key}{optional}: {render_type(value, defs)};")

        if isinstance(additional, dict):
            lines.append(f"  [key: string]: {render_type(additional, defs)};")

        lines.append("}")
        return "\n".join(lines)

    if "anyOf" in schema:
        return " | ".join(render_type(item, defs) for item in schema["anyOf"])

    raise ValueError(f"Unsupported schema: {schema}")


def render_model(model: type[BaseModel]) -> str:
    schema = model.model_json_schema()
    defs = schema.get("$defs", {})
    body = render_type(schema, defs)
    return f"export type {model.__name__} = {body};"


def render_union() -> str:
    members = " | ".join(UNION_MEMBERS)
    return f"export type {UNION_NAME} = {members};"


def render_guard() -> str:
    return """export const isStreamEvent = (value: unknown): value is StreamEvent => {
  if (!value || typeof value !== "object") {
    return false;
  }

  const event = (value as { event?: unknown }).event;
  const data = (value as { data?: unknown }).data;

  if (event === "message_delta") {
    return !!data && typeof (data as { text?: unknown }).text === "string";
  }

  if (event === "error") {
    return !!data && typeof (data as { message?: unknown }).message === "string";
  }

  return event === "done" && !!data && typeof data === "object";
};"""


def generate() -> str:
    sections = [
        "// This file is auto-generated from backend/schemas/events.py.",
        "// Do not edit manually.",
        "",
    ]

    for model in MODEL_ORDER:
        sections.append(render_model(model))
        sections.append("")

    sections.append(render_union())
    sections.append("")
    sections.append(render_guard())
    sections.append("")

    return "\n".join(sections)


def main() -> None:
    output = BACKEND_ROOT.parent / "app" / "src" / "types" / "events.ts"
    output.write_text(generate(), encoding="utf-8")
    print(f"Generated {output}")


if __name__ == "__main__":
    main()
