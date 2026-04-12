from pathlib import Path

import pytest

from diri_agent_toolbox.files import SandboxedFileToolbox


@pytest.mark.asyncio
async def test_read_write_list_stat(tmp_path: Path):
    box = SandboxedFileToolbox(tmp_path)
    w = await box.write_text("sub/hi.txt", "hello")
    assert w.success
    r = await box.read_text("sub/hi.txt")
    assert r.success and r.result == "hello"
    ls = await box.list_dir("sub")
    assert ls.success and "hi.txt" in (ls.result or [])
    st = await box.stat("sub/hi.txt")
    assert st.success and st.result and st.result["size"] == 5


@pytest.mark.asyncio
async def test_path_escape_denied(tmp_path: Path):
    box = SandboxedFileToolbox(tmp_path)
    r = await box.read_text("../outside")
    assert r.success is False
