from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from diri_agent_toolbox.contracts import BaseEvent
from diri_agent_toolbox.streaming import StreamTopics, validate_event


def test_stream_topics():
    assert StreamTopics.MODEL_EVENTS.value == "model-events"
    assert StreamTopics.INFERENCE_EVENTS.value == "inference-events"
    all_topics = StreamTopics.all()
    assert "model-events" in all_topics
    assert len(all_topics) == 5


def test_validate_event_fallsback_to_base():
    event = validate_event("unknown", {"event": "x", "source": "s"})
    assert isinstance(event, BaseEvent)


def test_validate_event_with_registered_schema():
    from diri_agent_toolbox.contracts import ModelReadyEvent
    from diri_agent_toolbox.streaming import register_topic_schema

    register_topic_schema("model-events", [ModelReadyEvent])
    event = validate_event(
        "model-events",
        {
            "event": "model-ready",
            "source": "reg",
            "model_name": "bert",
            "version": "1",
            "registry_path": "/m/b",
            "metadata": {},
        },
    )
    assert isinstance(event, ModelReadyEvent)


@pytest.mark.asyncio
async def test_streaming_client_publish():
    mock_redis_module = MagicMock()
    mock_instance = AsyncMock()
    mock_instance.xadd = AsyncMock(return_value="12345-0")
    mock_redis_module.from_url.return_value = mock_instance

    with patch.dict("sys.modules", {"redis.asyncio": mock_redis_module}):
        from diri_agent_toolbox.streaming import StreamingClient

        client = StreamingClient(redis_url="redis://localhost:6379/0")
        client.redis = mock_instance

        msg_id = await client.publish("test-topic", {"event": "test", "source": "s"})
        assert msg_id == "12345-0"
        mock_instance.xadd.assert_called_once()


@pytest.mark.asyncio
async def test_streaming_client_connect():
    mock_redis_module = MagicMock()
    mock_instance = AsyncMock()
    mock_instance.ping = AsyncMock()
    mock_redis_module.Redis.return_value = mock_instance
    mock_redis_module.from_url.return_value = mock_instance

    with patch.dict("sys.modules", {"redis.asyncio": mock_redis_module}):
        from diri_agent_toolbox.streaming import StreamingClient

        client = StreamingClient(redis_host="localhost", redis_port=6379)
        client.redis = mock_instance
        await client.connect()
        mock_instance.ping.assert_called_once()


@pytest.mark.asyncio
async def test_streaming_client_stop():
    mock_redis_module = MagicMock()

    with patch.dict("sys.modules", {"redis.asyncio": mock_redis_module}):
        from diri_agent_toolbox.streaming import StreamingClient

        client = StreamingClient(redis_url="redis://localhost:6379/0")
        assert client._running is False
        client._running = True
        client.stop()
        assert client._running is False


@pytest.mark.asyncio
async def test_streaming_client_disconnect():
    mock_redis_module = MagicMock()
    mock_instance = AsyncMock()
    mock_instance.close = AsyncMock()
    mock_redis_module.from_url.return_value = mock_instance

    with patch.dict("sys.modules", {"redis.asyncio": mock_redis_module}):
        from diri_agent_toolbox.streaming import StreamingClient

        client = StreamingClient(redis_url="redis://localhost:6379/0")
        client.redis = mock_instance
        await client.disconnect()
        mock_instance.close.assert_called_once()
