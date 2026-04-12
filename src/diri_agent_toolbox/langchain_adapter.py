"""Optional LangChain StructuredTool bridge (requires langchain-core)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from diri_agent_toolbox.models import ToolDefinition, ToolResult


def tool_result_to_message(r: ToolResult) -> dict[str, Any]:
    return {"success": r.success, "result": r.result, "error": r.error, "metadata": r.metadata}


def make_async_structured_tool(
    defn: ToolDefinition,
    executor: Callable[..., Awaitable[ToolResult]],
):
    """
    Build a LangChain StructuredTool that invokes an async toolbox function.
    """
    try:
        from importlib import import_module

        StructuredTool = import_module("langchain_core.tools").StructuredTool
    except ImportError as e:
        raise ImportError("Install diri-agent-toolbox[langchain] for LangChain support") from e

    async def _arun(**kwargs: Any) -> dict[str, Any]:
        r = await executor(**kwargs)
        return tool_result_to_message(r)

    return StructuredTool.from_function(
        coroutine=_arun,
        name=defn.name,
        description=defn.description,
    )
