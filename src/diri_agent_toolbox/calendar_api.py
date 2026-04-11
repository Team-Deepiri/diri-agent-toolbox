"""Calendar DTOs, protocol, and Google Calendar REST client (OAuth token supplied by host)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable
from urllib.parse import quote

from pydantic import BaseModel, Field

from diri_agent_toolbox.http import AsyncHttpToolbox
from diri_agent_toolbox.models import ToolResult


class CalendarEvent(BaseModel):
    """Normalized calendar event (subset of Google Calendar API resource)."""

    id: str | None = None
    summary: str | None = None
    description: str | None = None
    start: str | None = None
    end: str | None = None
    html_link: str | None = Field(default=None, alias="htmlLink")

    model_config = {"populate_by_name": True}


class CreateEventRequest(BaseModel):
    summary: str
    start_rfc3339: str = Field(description="RFC3339 datetime, e.g. 2026-04-11T10:00:00Z")
    end_rfc3339: str
    description: str | None = None


class ListEventsQuery(BaseModel):
    time_min: str | None = Field(default=None, description="RFC3339 lower bound")
    time_max: str | None = Field(default=None, description="RFC3339 upper bound")
    max_results: int = Field(default=25, ge=1, le=250)


@runtime_checkable
class CalendarClient(Protocol):
    async def list_events(self, query: ListEventsQuery) -> ToolResult: ...

    async def create_event(self, body: CreateEventRequest) -> ToolResult: ...


class GoogleCalendarClient:
    """
    Minimal Google Calendar API v3 client using the host-provided bearer token.
    Does not handle OAuth refresh; refresh in the host app and construct a new client.
    """

    BASE = "https://www.googleapis.com/calendar/v3"

    def __init__(
        self,
        access_token: str,
        calendar_id: str = "primary",
        *,
        http: AsyncHttpToolbox | None = None,
    ) -> None:
        self._calendar_id = calendar_id
        self._http = http or AsyncHttpToolbox(
            allowed_url_prefixes=[self.BASE + "/", "https://www.googleapis.com/calendar/v3/"],
            headers={"Authorization": f"Bearer {access_token}"},
        )

    def _cal_path(self) -> str:
        cid = quote(self._calendar_id, safe="@")
        return f"{self.BASE}/calendars/{cid}/events"

    async def list_events(self, query: ListEventsQuery) -> ToolResult:
        params: dict[str, Any] = {"maxResults": query.max_results, "singleEvents": "true"}
        if query.time_min:
            params["timeMin"] = query.time_min
        if query.time_max:
            params["timeMax"] = query.time_max
        url = self._cal_path()
        return await self._http.get(url, params=params)

    async def create_event(self, body: CreateEventRequest) -> ToolResult:
        payload: dict[str, Any] = {
            "summary": body.summary,
            "description": body.description,
            "start": {"dateTime": body.start_rfc3339},
            "end": {"dateTime": body.end_rfc3339},
        }
        url = self._cal_path()
        return await self._http.post(url, json_body=payload)

    async def aclose(self) -> None:
        await self._http.aclose()
