import asyncio

import pytest

from diri_agent_toolbox.processing import (
    AsyncBatchProcessor,
    AsyncItemProcessor,
    BatchProcessingConfig,
    BatchProcessingResult,
)


def test_batch_processing_result():
    r = BatchProcessingResult(
        total_items=100,
        processed_items=100,
        successful_items=80,
        failed_items=20,
        processing_time_seconds=5.0,
        errors=[{"error": "err"}],
    )
    assert r.success_rate == 0.8
    d = r.to_dict()
    assert d["success_rate"] == 0.8
    assert d["total_items"] == 100


def test_empty_result():
    r = BatchProcessingResult(
        total_items=0,
        processed_items=0,
        successful_items=0,
        failed_items=0,
        processing_time_seconds=0.0,
    )
    assert r.success_rate == 0.0


@pytest.mark.asyncio
async def test_async_batch_processor_success():
    config = BatchProcessingConfig(batch_size=10, max_concurrent_batches=2)
    processor = AsyncBatchProcessor(config)

    async def double(x: int) -> int:
        await asyncio.sleep(0.001)
        return x * 2

    result = await processor.process_batch(list(range(20)), double)
    assert result.total_items == 20
    assert result.successful_items == 20
    assert result.failed_items == 0
    assert result.success_rate == 1.0


@pytest.mark.asyncio
async def test_async_batch_processor_with_failures():
    config = BatchProcessingConfig(batch_size=5, max_concurrent_batches=2)
    processor = AsyncBatchProcessor(config)

    async def maybe_fail(x: int) -> int:
        await asyncio.sleep(0.001)
        if x % 2 == 0:
            raise ValueError(f"bad {x}")
        return x

    result = await processor.process_batch(list(range(10)), maybe_fail)
    assert result.total_items == 10
    assert result.successful_items == 5
    assert result.failed_items == 5
    assert len(result.errors) == 5


@pytest.mark.asyncio
async def test_async_batch_processor_progress_callback():
    config = BatchProcessingConfig(batch_size=5, max_concurrent_batches=2)
    processor = AsyncBatchProcessor(config)
    calls = []

    async def identity(x: int) -> int:
        return x

    def progress(current: int, total: int) -> None:
        calls.append((current, total))

    await processor.process_batch(list(range(10)), identity, progress_callback=progress)
    assert len(calls) > 0


@pytest.mark.asyncio
async def test_async_batch_processor_empty():
    config = BatchProcessingConfig(batch_size=10)
    processor = AsyncBatchProcessor(config)

    async def identity(x: int) -> int:
        return x

    result = await processor.process_batch([], identity)
    assert result.total_items == 0
    assert result.successful_items == 0


@pytest.mark.asyncio
async def test_async_item_processor():
    config = BatchProcessingConfig(batch_size=5, max_concurrent_batches=2)

    async def double(x: int) -> int:
        await asyncio.sleep(0.001)
        return x * 2

    ip = AsyncItemProcessor(double, config)
    results, result = await ip.process_items(list(range(10)))
    assert len(results) == 10
    assert result.successful_items == 10
    assert sum(results) == sum(x * 2 for x in range(10))


@pytest.mark.asyncio
async def test_async_item_processor_stream():
    config = BatchProcessingConfig(batch_size=3, max_concurrent_batches=2)

    async def double(x: int) -> int:
        return x * 2

    async def item_stream():
        for i in range(7):
            yield i

    ip = AsyncItemProcessor(double, config)
    results, result = await ip.process_stream(item_stream())
    assert len(results) == 7
    assert result.successful_items == 7
