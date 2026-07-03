"""Async sandboxed file operations under a fixed root directory."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

import aiofiles

from diri_agent_toolbox.errors import ValidationToolboxError
from diri_agent_toolbox.models import ToolResult


def _file_size(path: Path) -> int:
    return path.stat().st_size


def _resolve_under_root(root_dir: Path, relative: str) -> Path:
    """Resolve relative path and ensure it stays under root_dir."""
    root = root_dir.resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as e:
        raise ValidationToolboxError(
            f"Path escapes sandbox: {relative}",
            code="path_escape",
        ) from e
    return candidate


class SandboxedFileToolbox:
    """Read/write/list files only under `root_dir`."""

    def __init__(self, root_dir: Path, *, max_read_bytes: int = 5_000_000) -> None:
        self.root_dir = root_dir.resolve()
        self.max_read_bytes = max_read_bytes

    async def read_text(self, relative_path: str, *, encoding: str = "utf-8") -> ToolResult:
        try:
            path = _resolve_under_root(self.root_dir, relative_path)
            is_file = await asyncio.to_thread(path.is_file)
            if not is_file:
                return ToolResult(success=False, error="Not a file", metadata={"path": str(path)})
            size = await asyncio.to_thread(_file_size, path)
            if size > self.max_read_bytes:
                return ToolResult(
                    success=False,
                    error=f"File too large ({size} > {self.max_read_bytes})",
                    metadata={"path": str(path)},
                )
            async with aiofiles.open(path, encoding=encoding) as f:
                content = await f.read()
            meta = {"path": str(path), "size": size}
            return ToolResult(success=True, result=content, metadata=meta)
        except ValidationToolboxError as e:
            return ToolResult(success=False, error=e.message, metadata={"code": e.code or ""})
        except OSError as e:
            return ToolResult(success=False, error=str(e), metadata={"code": "os_error"})

    async def write_text(
        self,
        relative_path: str,
        content: str,
        *,
        encoding: str = "utf-8",
        max_write_bytes: int = 5_000_000,
    ) -> ToolResult:
        try:
            if len(content.encode(encoding)) > max_write_bytes:
                return ToolResult(success=False, error="Content exceeds max_write_bytes")
            path = _resolve_under_root(self.root_dir, relative_path)
            await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
            async with aiofiles.open(path, "w", encoding=encoding) as f:
                await f.write(content)
            return ToolResult(success=True, result=str(path), metadata={"path": str(path)})
        except ValidationToolboxError as e:
            return ToolResult(success=False, error=e.message, metadata={"code": e.code or ""})
        except OSError as e:
            return ToolResult(success=False, error=str(e), metadata={"code": "os_error"})

    async def list_dir(self, relative_path: str = ".") -> ToolResult:
        try:
            path = _resolve_under_root(self.root_dir, relative_path)
            is_dir = await asyncio.to_thread(path.is_dir)
            if not is_dir:
                return ToolResult(
                    success=False,
                    error="Not a directory",
                    metadata={"path": str(path)},
                )
            entries = await asyncio.to_thread(os.listdir, path)
            return ToolResult(success=True, result=sorted(entries), metadata={"path": str(path)})
        except ValidationToolboxError as e:
            return ToolResult(success=False, error=e.message, metadata={"code": e.code or ""})
        except OSError as e:
            return ToolResult(success=False, error=str(e), metadata={"code": "os_error"})

    async def stat(self, relative_path: str) -> ToolResult:
        try:
            path = _resolve_under_root(self.root_dir, relative_path)
            st = await asyncio.to_thread(path.stat)
            is_file = await asyncio.to_thread(path.is_file)
            is_dir = await asyncio.to_thread(path.is_dir)
            meta: dict[str, Any] = {
                "path": str(path),
                "size": st.st_size,
                "is_file": is_file,
                "is_dir": is_dir,
            }
            return ToolResult(success=True, result=meta)
        except ValidationToolboxError as e:
            return ToolResult(success=False, error=e.message, metadata={"code": e.code or ""})
        except OSError as e:
            return ToolResult(success=False, error=str(e), metadata={"code": "os_error"})

    async def delete(self, relative_path: str) -> ToolResult:
        try:
            path = _resolve_under_root(self.root_dir, relative_path)
            is_file = await asyncio.to_thread(path.is_file)
            if not is_file:
                return ToolResult(success=False, error="Not a file", metadata={"path": str(path)})
            await asyncio.to_thread(path.unlink)
            return ToolResult(success=True, result=f"Deleted {path}", metadata={"path": str(path)})
        except ValidationToolboxError as e:
            return ToolResult(success=False, error=e.message, metadata={"code": e.code or ""})
        except OSError as e:
            return ToolResult(success=False, error=str(e), metadata={"code": "os_error"})

    async def copy(self, src: str, dst: str) -> ToolResult:
        try:
            import shutil

            src_path = _resolve_under_root(self.root_dir, src)
            dst_path = _resolve_under_root(self.root_dir, dst)
            await asyncio.to_thread(shutil.copy2, src_path, dst_path)
            return ToolResult(
                success=True,
                result=f"Copied {src} to {dst}",
                metadata={"src": str(src_path), "dst": str(dst_path)},
            )
        except ValidationToolboxError as e:
            return ToolResult(success=False, error=e.message, metadata={"code": e.code or ""})
        except OSError as e:
            return ToolResult(success=False, error=str(e), metadata={"code": "os_error"})

    async def move(self, src: str, dst: str) -> ToolResult:
        try:
            import shutil

            src_path = _resolve_under_root(self.root_dir, src)
            dst_path = _resolve_under_root(self.root_dir, dst)
            await asyncio.to_thread(shutil.move, src_path, dst_path)
            return ToolResult(
                success=True,
                result=f"Moved {src} to {dst}",
                metadata={"src": str(src_path), "dst": str(dst_path)},
            )
        except ValidationToolboxError as e:
            return ToolResult(success=False, error=e.message, metadata={"code": e.code or ""})
        except OSError as e:
            return ToolResult(success=False, error=str(e), metadata={"code": "os_error"})

    async def read_binary(self, relative_path: str) -> ToolResult:
        try:
            path = _resolve_under_root(self.root_dir, relative_path)
            is_file = await asyncio.to_thread(path.is_file)
            if not is_file:
                return ToolResult(success=False, error="Not a file", metadata={"path": str(path)})
            size = await asyncio.to_thread(_file_size, path)
            if size > self.max_read_bytes:
                return ToolResult(
                    success=False,
                    error=f"File too large ({size} > {self.max_read_bytes})",
                    metadata={"path": str(path)},
                )
            async with aiofiles.open(path, "rb") as f:
                content = await f.read()
            return ToolResult(
                success=True, result=content, metadata={"path": str(path), "size": size}
            )
        except ValidationToolboxError as e:
            return ToolResult(success=False, error=e.message, metadata={"code": e.code or ""})
        except OSError as e:
            return ToolResult(success=False, error=str(e), metadata={"code": "os_error"})
