"""Async HTTP helpers with optional URL allowlist and basic SSRF mitigations."""

from __future__ import annotations

import ipaddress
from collections.abc import Callable
from datetime import datetime
from inspect import isawaitable
from typing import Any
from urllib.parse import urlparse

import httpx

from diri_agent_toolbox.errors import ValidationToolboxError
from diri_agent_toolbox.models import ToolResult

UrlPolicy = Callable[[str], Any]


def parse_json_or_text(response: httpx.Response) -> Any:
    """
    Parse an httpx response body as JSON when valid; otherwise return decoded text.

    Shared by ``AsyncHttpToolbox`` and available for callers that handle raw responses.
    """
    try:
        return response.json()
    except Exception:
        return response.text


def _is_literal_private_or_loopback_host(host: str) -> bool:
    """True if host is an IP string that is private, loopback, link-local, or reserved."""
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return bool(
        ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast
    )


def default_prefix_url_policy(url: str, allowed_prefixes: list[str] | None) -> bool:
    """True if URL is allowed. Empty/None allowed_prefixes skips prefix check."""
    if not allowed_prefixes:
        return True
    return any(url.startswith(p) for p in allowed_prefixes)


class AsyncHttpToolbox:
    """
    Shared httpx.AsyncClient for agent HTTP tools.

    - Optional `allowed_url_prefixes`: URL must start with one prefix string.
    - `block_private_hosts`: block literal private/loopback/link-local IP hosts.
    - `url_policy`: async or sync callable(url) -> bool; if False, request is rejected.
    """

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        allowed_url_prefixes: list[str] | None = None,
        url_policy: UrlPolicy | None = None,
        block_private_hosts: bool = True,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._timeout = timeout
        self._allowed_prefixes = allowed_url_prefixes
        self._url_policy = url_policy
        self._block_private_hosts = block_private_hosts
        self._client: httpx.AsyncClient | None = None
        self._default_headers = headers or {}

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                headers=self._default_headers,
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _enforce_policy(self, url: str) -> None:
        if not default_prefix_url_policy(url, self._allowed_prefixes):
            raise ValidationToolboxError(
                f"URL not allowed by prefix policy: {url}",
                code="url_prefix_denied",
            )
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValidationToolboxError(
                f"URL scheme not allowed: {parsed.scheme}",
                code="url_scheme_denied",
            )
        host = parsed.hostname
        if host is None:
            raise ValidationToolboxError("URL has no host", code="url_no_host")
        if self._block_private_hosts and _is_literal_private_or_loopback_host(host):
            raise ValidationToolboxError(
                f"Host not allowed (private/loopback IP): {host}",
                code="url_host_blocked",
            )
        if self._url_policy is not None:
            ok = self._url_policy(url)
            if isawaitable(ok):
                ok = await ok
            if not ok:
                raise ValidationToolboxError(
                    "URL rejected by custom url_policy",
                    code="url_policy_denied",
                )

    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> ToolResult:
        start = datetime.utcnow()
        try:
            await self._enforce_policy(url)
            client = await self._get_client()
            response = await client.get(url, headers=headers, params=params)
            return self._to_tool_result(response, start)
        except ValidationToolboxError as e:
            return ToolResult(success=False, error=e.message, metadata={"code": e.code or ""})
        except httpx.HTTPError as e:
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"code": "http_error"},
            )

    async def post(
        self,
        url: str,
        *,
        json_body: Any = None,
        headers: dict[str, str] | None = None,
    ) -> ToolResult:
        start = datetime.utcnow()
        try:
            await self._enforce_policy(url)
            client = await self._get_client()
            response = await client.post(url, json=json_body, headers=headers)
            return self._to_tool_result(response, start)
        except ValidationToolboxError as e:
            return ToolResult(success=False, error=e.message, metadata={"code": e.code or ""})
        except httpx.HTTPError as e:
            return ToolResult(success=False, error=str(e), metadata={"code": "http_error"})

    async def request(
        self,
        method: str,
        url: str,
        *,
        json_body: Any = None,
        query_params: dict[str, Any] | None = None,
        content: str | bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> ToolResult:
        """
        Generic request. Body rules:
        - GET/HEAD/DELETE: uses query_params only (no JSON body).
        - POST/PUT/PATCH: sends json_body if provided, else content.
        """
        start = datetime.utcnow()
        m = method.upper()
        try:
            await self._enforce_policy(url)
            client = await self._get_client()
            kw: dict[str, Any] = {"headers": headers}
            if m in ("GET", "HEAD", "DELETE"):
                kw["params"] = query_params
                response = await client.request(m, url, **kw)
            else:
                if json_body is not None:
                    kw["json"] = json_body
                elif content is not None:
                    kw["content"] = content
                if query_params:
                    kw["params"] = query_params
                response = await client.request(m, url, **kw)
            return self._to_tool_result(response, start)
        except ValidationToolboxError as e:
            return ToolResult(success=False, error=e.message, metadata={"code": e.code or ""})
        except httpx.HTTPError as e:
            return ToolResult(success=False, error=str(e), metadata={"code": "http_error"})

    def _to_tool_result(self, response: httpx.Response, start: datetime) -> ToolResult:
        elapsed_ms = (datetime.utcnow() - start).total_seconds() * 1000
        body = parse_json_or_text(response)
        return ToolResult(
            success=response.is_success,
            result=body,
            execution_time_ms=elapsed_ms,
            metadata={"status_code": response.status_code},
        )
