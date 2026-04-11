"""Generic CRM DTOs and REST client built on AsyncHttpToolbox."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from diri_agent_toolbox.http import AsyncHttpToolbox
from diri_agent_toolbox.models import ToolResult


class Contact(BaseModel):
    id: str | None = None
    email: str | None = None
    name: str | None = None
    phone: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class Company(BaseModel):
    id: str | None = None
    name: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class Deal(BaseModel):
    id: str | None = None
    name: str | None = None
    amount: float | None = None
    stage: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


AuthHeadersProvider = Callable[[], dict[str, str]]


class RestCrmClient:
    """
    Thin CRM client: performs HTTP GET/POST against `base_url` with auth headers.
    Path templates are host-specific; this class stays provider-agnostic.
    """

    def __init__(
        self,
        base_url: str,
        *,
        auth_headers: dict[str, str] | AuthHeadersProvider | None = None,
        http: AsyncHttpToolbox | None = None,
        allowed_url_prefixes: list[str] | None = None,
    ) -> None:
        self._base = base_url.rstrip("/")
        prefixes = allowed_url_prefixes or [self._base + "/"]
        self._auth_provider: dict[str, str] | AuthHeadersProvider | None = auth_headers
        self._http = http or AsyncHttpToolbox(allowed_url_prefixes=prefixes)

    def _headers(self) -> dict[str, str]:
        if self._auth_provider is None:
            return {}
        if callable(self._auth_provider):
            return self._auth_provider()
        return dict(self._auth_provider)

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        query_params: dict[str, Any] | None = None,
    ) -> ToolResult:
        url = f"{self._base}/{path.lstrip('/')}"
        headers = self._headers()
        return await self._http.request(
            method,
            url,
            json_body=json_body,
            query_params=query_params,
            headers=headers,
        )

    async def get_contact(self, contact_path: str) -> ToolResult:
        """GET `contact_path` relative to base_url (e.g. 'contacts/123')."""
        return await self.request_json("GET", contact_path)

    async def list_contacts(self, list_path: str = "contacts", *, limit: int = 50) -> ToolResult:
        return await self.request_json("GET", list_path, query_params={"limit": limit})

    async def aclose(self) -> None:
        await self._http.aclose()
