import httpx
import pytest

from diri_agent_toolbox.http import AsyncHttpToolbox, default_prefix_url_policy, parse_json_or_text


def test_parse_json_or_text_json():
    r = httpx.Response(200, json={"a": 1})
    assert parse_json_or_text(r) == {"a": 1}


def test_parse_json_or_text_plain_text():
    r = httpx.Response(200, content=b"not json")
    assert parse_json_or_text(r) == "not json"


def test_default_prefix_url_policy():
    assert default_prefix_url_policy("https://a.com/x", ["https://a.com/"]) is True
    assert default_prefix_url_policy("https://b.com/x", ["https://a.com/"]) is False
    assert default_prefix_url_policy("https://a.com/x", None) is True
    assert default_prefix_url_policy("https://a.com/x", []) is True


@pytest.mark.asyncio
async def test_http_get_mocked():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    toolbox = AsyncHttpToolbox(timeout=5.0, allowed_url_prefixes=["https://example.com/"])
    toolbox._client = httpx.AsyncClient(transport=transport, timeout=5.0)  # type: ignore[attr-defined]

    r = await toolbox.get("https://example.com/api")
    assert r.success is True
    assert r.result == {"ok": True}
    assert r.metadata.get("status_code") == 200
    await toolbox.aclose()


@pytest.mark.asyncio
async def test_http_blocks_private_ip():
    toolbox = AsyncHttpToolbox(block_private_hosts=True)
    r = await toolbox.get("http://127.0.0.1:8080/")
    assert r.success is False
    assert "not allowed" in (r.error or "").lower() or "private" in (r.error or "").lower()
    await toolbox.aclose()


@pytest.mark.asyncio
async def test_http_prefix_denied():
    toolbox = AsyncHttpToolbox(allowed_url_prefixes=["https://allowed.only/"])
    r = await toolbox.get("https://evil.com/")
    assert r.success is False
    await toolbox.aclose()
