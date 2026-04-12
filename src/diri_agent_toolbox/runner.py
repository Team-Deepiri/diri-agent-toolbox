"""Register portable tools by name and execute with unified timing."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from diri_agent_toolbox import data as data_ops
from diri_agent_toolbox.calendar_api import CalendarClient, CreateEventRequest, ListEventsQuery
from diri_agent_toolbox.crm import RestCrmClient
from diri_agent_toolbox.files import SandboxedFileToolbox
from diri_agent_toolbox.http import AsyncHttpToolbox
from diri_agent_toolbox.models import ToolCategory, ToolDefinition, ToolResult


class ToolRunner:
    """
    Facade: `execute(name, **kwargs) -> ToolResult`.
    Only registers tools for components passed in (e.g. no `http_*` without `http`).
    """

    def __init__(
        self,
        *,
        http: AsyncHttpToolbox | None = None,
        files: SandboxedFileToolbox | None = None,
        calendar: CalendarClient | None = None,
        crm: RestCrmClient | None = None,
    ) -> None:
        self._http = http
        self._files = files
        self._calendar = calendar
        self._crm = crm
        self._impls: dict[str, Callable[..., Awaitable[ToolResult]]] = {}
        self._defs: dict[str, ToolDefinition] = {}
        self._register_all()

    def _add(self, defn: ToolDefinition, impl: Callable[..., Awaitable[ToolResult]]) -> None:
        self._defs[defn.name] = defn
        self._impls[defn.name] = impl

    def _register_all(self) -> None:
        # Data tools (always)
        self._add(
            ToolDefinition(
                name="json_parse",
                description="Parse a JSON string into an object",
                category=ToolCategory.DATA,
                parameters={
                    "json_string": {"type": "string"},
                    "strict": {"type": "boolean", "description": "default true"},
                },
                required_params=["json_string"],
            ),
            lambda json_string, strict=True: data_ops.json_parse(json_string, strict=strict),
        )
        self._add(
            ToolDefinition(
                name="json_format",
                description="Format a value as JSON string",
                category=ToolCategory.DATA,
                parameters={
                    "data": {"type": "object"},
                    "indent": {"type": "integer"},
                },
                required_params=["data"],
            ),
            lambda data, indent=2: data_ops.json_format(data, indent=indent),
        )
        self._add(
            ToolDefinition(
                name="data_transform",
                description="Map fields from data using new_key -> old_key mapping",
                category=ToolCategory.DATA,
                parameters={
                    "data": {"type": "object"},
                    "mapping": {"type": "object"},
                },
                required_params=["data", "mapping"],
            ),
            lambda data, mapping: data_ops.data_transform(data, mapping),
        )
        self._add(
            ToolDefinition(
                name="calculate",
                description="Evaluate a safe numeric expression (no eval)",
                category=ToolCategory.MATH,
                parameters={"expression": {"type": "string"}},
                required_params=["expression"],
            ),
            lambda expression: data_ops.calculate(expression),
        )
        self._add(
            ToolDefinition(
                name="statistics",
                description="Compute mean, median, std, min, max, sum for a list of numbers",
                category=ToolCategory.MATH,
                parameters={
                    "numbers": {"type": "array"},
                    "operations": {"type": "array", "items": {"type": "string"}},
                },
                required_params=["numbers"],
            ),
            lambda numbers, operations=None: data_ops.statistics_tool(numbers, operations),
        )
        self._add(
            ToolDefinition(
                name="text_summarize",
                description="Very simple extractive summary",
                category=ToolCategory.TEXT,
                parameters={
                    "text": {"type": "string"},
                    "max_length": {"type": "integer"},
                },
                required_params=["text"],
            ),
            lambda text, max_length=200: data_ops.text_summarize(text, max_length=max_length),
        )
        self._add(
            ToolDefinition(
                name="text_extract",
                description="Regex-based extraction for field labels in text",
                category=ToolCategory.TEXT,
                parameters={
                    "text": {"type": "string"},
                    "fields": {"type": "array", "items": {"type": "string"}},
                },
                required_params=["text", "fields"],
            ),
            lambda text, fields: data_ops.text_extract(text, fields),
        )
        self._add(
            ToolDefinition(
                name="current_time",
                description="Current time as formatted string (IANA timezone or UTC)",
                category=ToolCategory.DATA,
                parameters={
                    "timezone": {"type": "string"},
                    "format": {"type": "string"},
                },
                required_params=[],
            ),
            lambda timezone="UTC", format="%Y-%m-%d %H:%M:%S": data_ops.current_time(
                timezone_name=timezone,
                format=format,
            ),
        )

        if self._http is not None:
            h = self._http

            async def http_get(
                url: str,
                headers: dict[str, str] | None = None,
                params: dict | None = None,
            ):
                return await h.get(url, headers=headers, params=params)

            async def http_post(
                url: str,
                data: dict | None = None,
                headers: dict[str, str] | None = None,
            ):
                return await h.post(url, json_body=data, headers=headers)

            async def http_request(
                method: str,
                url: str,
                data: dict | None = None,
                headers: dict[str, str] | None = None,
            ):
                m = method.upper()
                if m in ("GET", "HEAD", "DELETE"):
                    return await h.request(m, url, query_params=data, headers=headers)
                return await h.request(m, url, json_body=data, headers=headers)

            self._add(
                ToolDefinition(
                    name="http_get",
                    description="HTTP GET",
                    category=ToolCategory.HTTP,
                    parameters={
                        "url": {"type": "string"},
                        "headers": {"type": "object"},
                        "params": {"type": "object"},
                    },
                    required_params=["url"],
                ),
                http_get,
            )
            self._add(
                ToolDefinition(
                    name="http_post",
                    description="HTTP POST with JSON body",
                    category=ToolCategory.HTTP,
                    parameters={
                        "url": {"type": "string"},
                        "data": {"type": "object"},
                        "headers": {"type": "object"},
                    },
                    required_params=["url"],
                ),
                http_post,
            )
            self._add(
                ToolDefinition(
                    name="http_request",
                    description="HTTP request; GET uses data as query params, POST as JSON body",
                    category=ToolCategory.HTTP,
                    parameters={
                        "method": {"type": "string"},
                        "url": {"type": "string"},
                        "data": {"type": "object"},
                        "headers": {"type": "object"},
                    },
                    required_params=["method", "url"],
                ),
                http_request,
            )

        if self._files is not None:
            f = self._files

            self._add(
                ToolDefinition(
                    name="file_read",
                    description="Read a text file under the sandbox root",
                    category=ToolCategory.FILE,
                    parameters={
                        "path": {"type": "string"},
                        "encoding": {"type": "string"},
                    },
                    required_params=["path"],
                ),
                lambda path, encoding="utf-8": f.read_text(path, encoding=encoding),
            )
            self._add(
                ToolDefinition(
                    name="file_write",
                    description="Write text to a path under the sandbox root",
                    category=ToolCategory.FILE,
                    parameters={
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                        "encoding": {"type": "string"},
                    },
                    required_params=["path", "content"],
                ),
                lambda path, content, encoding="utf-8": f.write_text(
                    path, content, encoding=encoding
                ),
            )
            self._add(
                ToolDefinition(
                    name="file_list_dir",
                    description="List directory entries under the sandbox root",
                    category=ToolCategory.FILE,
                    parameters={"path": {"type": "string"}},
                    required_params=[],
                ),
                lambda path=".": f.list_dir(path),
            )
            self._add(
                ToolDefinition(
                    name="file_stat",
                    description="File metadata under the sandbox root",
                    category=ToolCategory.FILE,
                    parameters={"path": {"type": "string"}},
                    required_params=["path"],
                ),
                lambda path: f.stat(path),
            )

        if self._calendar is not None:
            cal = self._calendar

            async def calendar_list_events(
                time_min: str | None = None,
                time_max: str | None = None,
                max_results: int = 25,
            ):
                q = ListEventsQuery(time_min=time_min, time_max=time_max, max_results=max_results)
                return await cal.list_events(q)

            async def calendar_create_event(
                summary: str,
                start_rfc3339: str,
                end_rfc3339: str,
                description: str | None = None,
            ):
                body = CreateEventRequest(
                    summary=summary,
                    start_rfc3339=start_rfc3339,
                    end_rfc3339=end_rfc3339,
                    description=description,
                )
                return await cal.create_event(body)

            self._add(
                ToolDefinition(
                    name="calendar_list_events",
                    description="List events from the configured calendar",
                    category=ToolCategory.CALENDAR,
                    parameters={
                        "time_min": {"type": "string"},
                        "time_max": {"type": "string"},
                        "max_results": {"type": "integer"},
                    },
                    required_params=[],
                ),
                calendar_list_events,
            )
            self._add(
                ToolDefinition(
                    name="calendar_create_event",
                    description="Create a calendar event (RFC3339 start/end)",
                    category=ToolCategory.CALENDAR,
                    parameters={
                        "summary": {"type": "string"},
                        "start_rfc3339": {"type": "string"},
                        "end_rfc3339": {"type": "string"},
                        "description": {"type": "string"},
                    },
                    required_params=["summary", "start_rfc3339", "end_rfc3339"],
                ),
                calendar_create_event,
            )

        if self._crm is not None:
            crm = self._crm

            async def crm_request(
                method: str,
                path: str,
                json_body: dict | None = None,
                query_params: dict | None = None,
            ):
                return await crm.request_json(
                    method,
                    path,
                    json_body=json_body,
                    query_params=query_params,
                )

            self._add(
                ToolDefinition(
                    name="crm_request",
                    description="Authenticated JSON request to CRM base URL",
                    category=ToolCategory.CRM,
                    parameters={
                        "method": {"type": "string"},
                        "path": {"type": "string"},
                        "json_body": {"type": "object"},
                        "query_params": {"type": "object"},
                    },
                    required_params=["method", "path"],
                ),
                crm_request,
            )

    def list_tools(self, category: ToolCategory | None = None) -> list[ToolDefinition]:
        tools = list(self._defs.values())
        if category is not None:
            tools = [t for t in tools if t.category == category]
        return tools

    def get_tool(self, name: str) -> ToolDefinition | None:
        return self._defs.get(name)

    async def execute(self, tool_name: str, **kwargs: Any) -> ToolResult:
        if tool_name not in self._impls:
            return ToolResult(success=False, error=f"Tool not found: {tool_name}")
        impl = self._impls[tool_name]
        start = datetime.utcnow()
        try:
            out = await impl(**kwargs)
            elapsed = (datetime.utcnow() - start).total_seconds() * 1000
            if out.execution_time_ms == 0.0:
                out.execution_time_ms = elapsed
            return out
        except TypeError as e:
            return ToolResult(success=False, error=f"Bad arguments: {e}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def format_for_prompt(self) -> str:
        lines: list[str] = ["Available tools:"]
        for cat in ToolCategory:
            ts = [t for t in self._defs.values() if t.category == cat]
            if not ts:
                continue
            lines.append(f"\n## {cat.value.upper()}")
            for t in ts:
                lines.append(f"- **{t.name}**: {t.description}")
                if t.required_params:
                    lines.append(f"  Required: {', '.join(t.required_params)}")
        return "\n".join(lines)
