"""Portable JSON, math, statistics, and text helpers (no unsafe eval)."""

from __future__ import annotations

import ast
import json
import math
import operator as op
import re
import statistics
from datetime import datetime, timezone
from typing import Any, List, Union

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None  # type: ignore[misc, assignment]

from diri_agent_toolbox.models import ToolResult

# ---------------------------------------------------------------------------
# Safe math (ast-based; no eval)
# ---------------------------------------------------------------------------

_BINOPS: dict[type[ast.operator], Any] = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
}

_UNARY: dict[type[ast.unaryop], Any] = {
    ast.UAdd: op.pos,
    ast.USub: op.neg,
}

_ALLOWED_FUNCS: dict[str, Any] = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "pow": pow,
    "sum": sum,
    "len": len,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
}

_ALLOWED_NAMES: dict[str, float] = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
}


def _eval_ast(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        raise ValueError("Only numeric constants are allowed")

    if isinstance(node, ast.BinOp):
        if type(node.op) not in _BINOPS:
            raise ValueError("Binary operator not allowed")
        return _BINOPS[type(node.op)](_eval_ast(node.left), _eval_ast(node.right))

    if isinstance(node, ast.UnaryOp):
        if type(node.op) not in _UNARY:
            raise ValueError("Unary operator not allowed")
        return _UNARY[type(node.op)](_eval_ast(node.operand))

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only simple function names are allowed")
        fname = node.func.id
        if fname not in _ALLOWED_FUNCS:
            raise ValueError(f"Function not allowed: {fname}")
        fn = _ALLOWED_FUNCS[fname]
        args = [_eval_ast(a) for a in node.args]
        if node.keywords:
            raise ValueError("Keyword arguments are not allowed")
        return fn(*args)

    if isinstance(node, ast.Name):
        if node.id in _ALLOWED_NAMES:
            return _ALLOWED_NAMES[node.id]
        raise ValueError(f"Name not allowed: {node.id}")

    raise ValueError("Expression contains disallowed syntax")


def safe_calculate(expression: str) -> Any:
    """Evaluate a numeric expression using a restricted AST (no eval)."""
    tree = ast.parse(expression, mode="eval")
    return _eval_ast(tree.body)


# ---------------------------------------------------------------------------
# Async tool-shaped APIs returning ToolResult
# ---------------------------------------------------------------------------


async def json_parse(json_string: str, *, strict: bool = True) -> ToolResult:
    try:
        if strict:
            data = json.loads(json_string)
        else:
            data = json.loads(json_string, strict=False)
        return ToolResult(success=True, result=data)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def json_format(data: Any, *, indent: int = 2) -> ToolResult:
    try:
        out = json.dumps(data, indent=indent, default=str)
        return ToolResult(success=True, result=out)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def data_transform(data: dict[str, Any], mapping: dict[str, str]) -> ToolResult:
    try:
        result: dict[str, Any] = {}
        for new_key, old_key in mapping.items():
            if old_key in data:
                result[new_key] = data[old_key]
            elif "." in old_key:
                value: Any = data
                for part in old_key.split("."):
                    if isinstance(value, dict):
                        value = value.get(part)
                    else:
                        value = None
                        break
                result[new_key] = value
            else:
                result[new_key] = None
        return ToolResult(success=True, result=result)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def calculate(expression: str) -> ToolResult:
    try:
        value = safe_calculate(expression)
        return ToolResult(success=True, result=value)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def statistics_tool(
    numbers: List[Union[int, float]],
    operations: list[str] | None = None,
) -> ToolResult:
    try:
        ops = operations or ["mean", "median", "std", "min", "max", "sum"]
        result: dict[str, Any] = {}
        for op_name in ops:
            if op_name == "mean":
                result["mean"] = statistics.mean(numbers)
            elif op_name == "median":
                result["median"] = statistics.median(numbers)
            elif op_name == "std":
                result["std"] = statistics.stdev(numbers) if len(numbers) > 1 else 0.0
            elif op_name == "min":
                result["min"] = min(numbers)
            elif op_name == "max":
                result["max"] = max(numbers)
            elif op_name == "sum":
                result["sum"] = sum(numbers)
        result["count"] = len(numbers)
        return ToolResult(success=True, result=result)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def text_summarize(text: str, max_length: int = 200) -> ToolResult:
    try:
        sentences = text.replace("\n", " ").split(". ")
        if len(sentences) <= 2:
            return ToolResult(success=True, result=text[:max_length])
        summary = f"{sentences[0]}. {sentences[-1]}"
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
        return ToolResult(success=True, result=summary)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def text_extract(text: str, fields: list[str]) -> ToolResult:
    try:
        result: dict[str, str | None] = {}
        text_lower = text.lower()
        for field in fields:
            pattern = rf"{re.escape(field.lower())}[:\s]+([^\n,;]+)"
            match = re.search(pattern, text_lower)
            if match:
                result[field] = match.group(1).strip()
            else:
                result[field] = None
        return ToolResult(success=True, result=result)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def current_time(timezone_name: str = "UTC", format: str = "%Y-%m-%d %H:%M:%S") -> ToolResult:
    """Return formatted local time for timezone_name (IANA) or UTC fallback."""
    try:
        if ZoneInfo is not None and timezone_name.upper() != "UTC":
            try:
                tz = ZoneInfo(timezone_name)
                now = datetime.now(tz)
            except Exception:
                now = datetime.now(timezone.utc)
        else:
            now = datetime.now(timezone.utc)
        return ToolResult(
            success=True,
            result=now.strftime(format),
            metadata={"timezone": timezone_name},
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))
