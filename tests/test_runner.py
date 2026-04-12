from pathlib import Path

import pytest

from diri_agent_toolbox.files import SandboxedFileToolbox
from diri_agent_toolbox.http import AsyncHttpToolbox
from diri_agent_toolbox.runner import ToolRunner


@pytest.mark.asyncio
async def test_runner_calculate():
    r = ToolRunner()
    out = await r.execute("calculate", expression="1+2*3")
    assert out.success and out.result == 7


@pytest.mark.asyncio
async def test_runner_with_http_mocked(monkeypatch):
    import httpx

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"x": 1})

    transport = httpx.MockTransport(handler)
    http = AsyncHttpToolbox(allowed_url_prefixes=["https://api.test/"])
    http._client = httpx.AsyncClient(transport=transport, timeout=5.0)  # type: ignore[attr-defined]
    runner = ToolRunner(http=http)
    out = await runner.execute("http_get", url="https://api.test/x")
    assert out.success and out.result == {"x": 1}
    await http.aclose()


@pytest.mark.asyncio
async def test_runner_files(tmp_path: Path):
    box = SandboxedFileToolbox(tmp_path)
    runner = ToolRunner(files=box)
    await runner.execute("file_write", path="a.txt", content="z")
    out = await runner.execute("file_read", path="a.txt")
    assert out.success and out.result == "z"
