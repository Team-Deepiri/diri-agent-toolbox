"""Pydantic models for tool results, definitions, and LLM JSON Schema export."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolCategory(str, Enum):
    """High-level grouping for tools (aligned with Cyrex-style categories)."""

    HTTP = "http"
    FILE = "file"
    MATH = "math"
    TEXT = "text"
    DATA = "data"
    CALENDAR = "calendar"
    CRM = "crm"
    DATABASE = "database"
    CACHE = "cache"
    STREAMING = "streaming"
    DEVICE = "device"
    CONFIDENCE = "confidence"
    PROCESSING = "processing"
    MONITORING = "monitoring"
    LOGGING = "logging"
    SYSTEM = "system"


class ToolResult(BaseModel):
    """Normalized outcome of a tool invocation."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    success: bool
    result: Any = None
    error: str | None = None
    execution_time_ms: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolDefinition(BaseModel):
    """Metadata for registering a tool with an agent or LLM."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    category: ToolCategory
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON-Schema-style parameter description (properties/required) or loose dict",
    )
    required_params: list[str] = Field(default_factory=list)
    returns: str = "Any"
    examples: list[dict[str, Any]] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "parameters": self.parameters,
            "required_params": self.required_params,
            "returns": self.returns,
            "examples": self.examples,
        }


def tool_definition_parameters_schema(defn: ToolDefinition) -> dict[str, Any]:
    """
    Build an OpenAI-style JSON Schema object for `parameters` (type object + properties + required).
    If `defn.parameters` already contains 'type' and 'properties', it is returned normalized.
    Otherwise `defn.parameters` is treated as a map of property name -> sub-schema dicts.
    """
    p = defn.parameters
    if p.get("type") == "object" and "properties" in p:
        out = {
            "type": "object",
            "properties": dict(p.get("properties") or {}),
            "required": list(p.get("required") or defn.required_params),
        }
        return out

    properties: dict[str, Any] = {}
    for key, val in p.items():
        if isinstance(val, dict):
            properties[key] = val
        else:
            properties[key] = {"type": "string", "description": str(val)}
    return {
        "type": "object",
        "properties": properties,
        "required": list(defn.required_params),
    }


def tool_definition_to_json_schema(defn: ToolDefinition) -> dict[str, Any]:
    """Return only the `parameters` JSON Schema fragment for function-calling."""
    return tool_definition_parameters_schema(defn)


def tool_definition_to_openai_function(defn: ToolDefinition) -> dict[str, Any]:
    """OpenAI Chat Completions `tools[]` entry shape (type function)."""
    return {
        "type": "function",
        "function": {
            "name": defn.name,
            "description": defn.description,
            "parameters": tool_definition_parameters_schema(defn),
        },
    }
