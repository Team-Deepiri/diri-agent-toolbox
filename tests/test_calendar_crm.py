import httpx
import pytest

from diri_agent_toolbox.calendar_api import GoogleCalendarClient, ListEventsQuery
from diri_agent_toolbox.crm import RestCrmClient
from diri_agent_toolbox.http import AsyncHttpToolbox


@pytest.mark.asyncio
async def test_google_calendar_list_mocked():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "calendar" in str(request.url)
        return httpx.Response(200, json={"items": []})

    transport = httpx.MockTransport(handler)
    prefixes = ["https://www.googleapis.com/calendar/v3/"]
    http_inner = AsyncHttpToolbox(allowed_url_prefixes=prefixes)
    http_inner._client = httpx.AsyncClient(transport=transport, timeout=5.0)  # type: ignore[attr-defined]
    client = GoogleCalendarClient("fake-token", http=http_inner)
    r = await client.list_events(ListEventsQuery())
    assert r.success
    await client.aclose()


@pytest.mark.asyncio
async def test_rest_crm_request():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "1"})

    transport = httpx.MockTransport(handler)

    h = AsyncHttpToolbox(allowed_url_prefixes=["https://crm.example/"])
    h._client = httpx.AsyncClient(transport=transport, timeout=5.0)  # type: ignore[attr-defined]
    crm = RestCrmClient("https://crm.example", auth_headers={"X-Key": "k"}, http=h)
    r = await crm.get_contact("contacts/1")
    assert r.success and r.result == {"id": "1"}
    await crm.aclose()
