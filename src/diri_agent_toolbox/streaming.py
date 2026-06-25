from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncIterator, Callable, Dict, Optional, cast

from diri_agent_toolbox.contracts import BaseEvent


class StreamTopics(str, Enum):
    MODEL_EVENTS = "model-events"
    INFERENCE_EVENTS = "inference-events"
    PLATFORM_EVENTS = "platform-events"
    AGI_DECISIONS = "agi-decisions"
    TRAINING_EVENTS = "training-events"

    @classmethod
    def all(cls) -> list[str]:
        return [t.value for t in cls]


TOPIC_EVENT_SCHEMAS: Dict[str, list] = {}


def register_topic_schema(topic: str, event_classes: list) -> None:
    TOPIC_EVENT_SCHEMAS[topic] = event_classes


def validate_event(topic: str, event_data: dict) -> BaseEvent:
    schemas = TOPIC_EVENT_SCHEMAS.get(topic)
    if schemas:
        for schema in schemas:
            try:
                return schema(**event_data)  # type: ignore[no-any-return]
            except Exception:
                continue
    return BaseEvent(**event_data)  # type: ignore[no-any-return]


class StreamingClient:
    def __init__(
        self,
        redis_url: Optional[str] = None,
        redis_host: str = "redis",
        redis_port: int = 6379,
        redis_password: Optional[str] = None,
    ):
        import redis.asyncio as redis

        if redis_url:
            self.redis = redis.from_url(redis_url, decode_responses=True)
        else:
            self.redis = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                decode_responses=True,
            )
        self._running = False

    async def connect(self) -> None:
        await self.redis.ping()

    async def disconnect(self) -> None:
        await self.redis.close()

    async def publish(
        self,
        topic: str,
        event: Dict[str, Any],
        max_length: Optional[int] = 10000,
    ) -> str:
        if "timestamp" not in event:
            event["timestamp"] = datetime.now(timezone.utc).isoformat()
        message_id = await self.redis.xadd(
            topic,
            cast(Any, event),
            maxlen=max_length,
            approximate=True,
        )
        return str(message_id)

    async def subscribe(
        self,
        topic: str,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        consumer_group: Optional[str] = None,
        consumer_name: Optional[str] = None,
        last_id: str = "0",
        block_ms: int = 1000,
    ) -> AsyncIterator[Dict[str, Any]]:
        import redis.asyncio as redis

        if consumer_group:
            try:
                await self.redis.xgroup_create(topic, consumer_group, id="0", mkstream=True)
            except redis.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise

        self._running = True

        while self._running:
            try:
                if consumer_group and consumer_name:
                    messages = cast(
                        list[tuple[str, list[tuple[str, dict[str, Any]]]]],
                        await self.redis.xreadgroup(
                            consumer_group,
                            consumer_name,
                            {topic: ">"},
                            count=10,
                            block=block_ms,
                        )
                        or [],
                    )
                else:
                    messages = cast(
                        list[tuple[str, list[tuple[str, dict[str, Any]]]]],
                        await self.redis.xread({topic: last_id}, count=10, block=block_ms)
                        or [],
                    )

                for _stream_name, stream_messages in messages:
                    for msg_id, data in stream_messages:
                        yield data
                        if callback:
                            try:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(data)
                                else:
                                    callback(data)
                            except Exception:
                                pass
                        last_id = msg_id
                        if consumer_group and consumer_name:
                            await self.redis.xack(topic, consumer_group, msg_id)

            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(1)

    async def subscribe_async(
        self,
        topic: str,
        callback: Callable[[Dict[str, Any]], None],
        consumer_group: Optional[str] = None,
        consumer_name: Optional[str] = None,
    ) -> None:
        async for _ in self.subscribe(topic, callback, consumer_group, consumer_name):
            pass

    def stop(self) -> None:
        self._running = False

    async def get_stream_info(self, topic: str) -> Dict[str, Any]:
        info = await self.redis.xinfo_stream(topic)
        return dict(info)  # type: ignore[no-any-return]

    async def get_stream_length(self, topic: str) -> int:
        return await self.redis.xlen(topic)  # type: ignore[no-any-return]
