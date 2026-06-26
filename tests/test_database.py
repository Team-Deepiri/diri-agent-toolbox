from unittest.mock import AsyncMock, MagicMock

import pytest

from diri_agent_toolbox.database import DatabaseToolbox


def _mock_pool(conn_mock):
    """Create a pool mock where acquire() returns an async context manager yielding conn_mock."""
    pool = MagicMock()
    ctx_manager = MagicMock()
    ctx_manager.__aenter__ = AsyncMock(return_value=conn_mock)
    ctx_manager.__aexit__ = AsyncMock(return_value=None)
    pool.acquire.return_value = ctx_manager
    pool.close = AsyncMock()
    return pool


@pytest.mark.asyncio
async def test_query_select():
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[{"id": 1, "name": "alice"}, {"id": 2, "name": "bob"}])
    pool = _mock_pool(conn)

    db = DatabaseToolbox(pool=pool)
    result = await db.query("SELECT * FROM users")
    assert result.success is True
    assert len(result.result) == 2
    assert result.result[0]["name"] == "alice"
    assert result.metadata["row_count"] == 2


@pytest.mark.asyncio
async def test_query_rejects_non_select():
    db = DatabaseToolbox()
    result = await db.query("DELETE FROM users")
    assert result.success is False
    assert "Only SELECT" in result.error


@pytest.mark.asyncio
async def test_query_error():
    conn = MagicMock()
    conn.fetch = AsyncMock(side_effect=Exception("connection failed"))
    pool = _mock_pool(conn)

    db = DatabaseToolbox(pool=pool)
    result = await db.query("SELECT * FROM users")
    assert result.success is False
    assert "connection failed" in result.error


@pytest.mark.asyncio
async def test_execute():
    conn = MagicMock()
    conn.execute = AsyncMock(return_value="INSERT 0 1")
    pool = _mock_pool(conn)

    db = DatabaseToolbox(pool=pool)
    result = await db.execute("INSERT INTO users (name) VALUES ($1)", "alice")
    assert result.success is True
    assert result.result == "INSERT 0 1"


@pytest.mark.asyncio
async def test_execute_error():
    pool = MagicMock()
    ctx_manager = MagicMock()
    ctx_manager.__aenter__ = AsyncMock(side_effect=Exception("db down"))
    ctx_manager.__aexit__ = AsyncMock(return_value=None)
    pool.acquire.return_value = ctx_manager

    db = DatabaseToolbox(pool=pool)
    result = await db.execute("UPDATE users SET name = $1", "bob")
    assert result.success is False


@pytest.mark.asyncio
async def test_get_tables():
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[{"table_name": "users"}, {"table_name": "orders"}])
    pool = _mock_pool(conn)

    db = DatabaseToolbox(pool=pool)
    result = await db.get_tables()
    assert result.success is True
    assert result.result == ["users", "orders"]


@pytest.mark.asyncio
async def test_get_tables_error():
    pool = MagicMock()
    ctx_manager = MagicMock()
    ctx_manager.__aenter__ = AsyncMock(side_effect=Exception("no connection"))
    ctx_manager.__aexit__ = AsyncMock(return_value=None)
    pool.acquire.return_value = ctx_manager

    db = DatabaseToolbox(pool=pool)
    result = await db.get_tables()
    assert result.success is False


@pytest.mark.asyncio
async def test_close():
    pool = MagicMock()
    pool.close = AsyncMock()

    db = DatabaseToolbox(pool=pool)
    await db.close()
    pool.close.assert_called_once()
    assert db._pool is None


@pytest.mark.asyncio
async def test_no_pool_no_dsn():
    db = DatabaseToolbox()
    result = await db.query("SELECT 1")
    assert result.success is False
