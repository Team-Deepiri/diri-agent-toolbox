from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from diri_agent_toolbox.models import ToolResult


class DatabaseToolbox:
    def __init__(self, pool: Any = None, dsn: Optional[str] = None):
        self._pool = pool
        self._dsn = dsn
        self._asyncpg = None

    async def _get_pool(self) -> Any:
        if self._pool is not None:
            return self._pool
        if self._dsn is not None:
            import asyncpg  # type: ignore[import-not-found]

            self._pool = await asyncpg.create_pool(self._dsn)
            return self._pool
        raise RuntimeError("No database pool or DSN configured")

    async def query(self, query: str, *params: Any, max_rows: int = 1000) -> ToolResult:
        start = datetime.now(timezone.utc)
        try:
            if not query.strip().upper().startswith("SELECT"):
                return ToolResult(
                    success=False,
                    error="Only SELECT queries are allowed",
                    metadata={"code": "query_not_allowed"},
                )
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
            result = [dict(row) for row in rows[:max_rows]]
            elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            return ToolResult(
                success=True,
                result=result,
                execution_time_ms=elapsed,
                metadata={"row_count": len(result)},
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e), metadata={"code": "db_error"})

    async def execute(self, query: str, *params: Any) -> ToolResult:
        start = datetime.now(timezone.utc)
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                result = await conn.execute(query, *params)
            elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            return ToolResult(success=True, result=result, execution_time_ms=elapsed)
        except Exception as e:
            return ToolResult(success=False, error=str(e), metadata={"code": "db_error"})

    async def get_tables(self) -> ToolResult:
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' ORDER BY table_name"
                )
            tables = [row["table_name"] for row in rows]
            return ToolResult(success=True, result=tables)
        except Exception as e:
            return ToolResult(success=False, error=str(e), metadata={"code": "db_error"})

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
