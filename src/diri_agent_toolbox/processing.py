from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, cast


@dataclass
class BatchProcessingConfig:
    batch_size: int = 100
    max_concurrent_batches: int = 5
    chunk_size: int = 1000
    chunk_overlap: int = 200
    enable_progress: bool = True
    retry_on_failure: bool = True
    max_retries: int = 3
    retry_delay_seconds: float = 1.0


@dataclass
class BatchProcessingResult:
    total_items: int
    processed_items: int
    successful_items: int
    failed_items: int
    processing_time_seconds: float
    errors: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_items == 0:
            return 0.0
        return self.successful_items / self.total_items

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_items": self.total_items,
            "processed_items": self.processed_items,
            "successful_items": self.successful_items,
            "failed_items": self.failed_items,
            "processing_time_seconds": self.processing_time_seconds,
            "success_rate": self.success_rate,
            "errors": self.errors,
        }


class AsyncBatchProcessor:
    def __init__(self, config: BatchProcessingConfig):
        self.config = config
        self.semaphore = asyncio.Semaphore(config.max_concurrent_batches)

    async def process_batch(
        self,
        items: List[Any],
        processor_func: Callable[[Any], Coroutine[Any, Any, Any]],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> BatchProcessingResult:
        start_time = time.time()
        total_items = len(items)
        successful_items = 0
        failed_items = 0
        errors: List[Dict[str, Any]] = []

        batches = [
            items[i : i + self.config.batch_size]
            for i in range(0, total_items, self.config.batch_size)
        ]

        tasks = [
            self._process_single_batch(batch, idx, processor_func, progress_callback)
            for idx, batch in enumerate(batches)
        ]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in batch_results:
            if isinstance(result, Exception):
                failed_items += self.config.batch_size
                errors.append({"error": str(result), "type": type(result).__name__})
            else:
                r = cast("dict[str, Any]", result)
                successful_items += r["successful"]
                failed_items += r["failed"]
                errors.extend(r.get("errors", []))

        return BatchProcessingResult(
            total_items=total_items,
            processed_items=total_items,
            successful_items=successful_items,
            failed_items=failed_items,
            processing_time_seconds=time.time() - start_time,
            errors=errors,
        )

    async def _process_single_batch(
        self,
        batch: List[Any],
        batch_idx: int,
        processor_func: Callable[[Any], Coroutine[Any, Any, Any]],
        progress_callback: Optional[Callable[[int, int], None]],
    ) -> Dict[str, Any]:
        async with self.semaphore:
            successful = 0
            failed = 0
            errors: List[Dict[str, Any]] = []

            tasks = [processor_func(item) for item in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for idx, result in enumerate(results):
                if isinstance(result, Exception):
                    failed += 1
                    errors.append(
                        {
                            "item_index": batch_idx * self.config.batch_size + idx,
                            "error": str(result),
                            "type": type(result).__name__,
                        }
                    )
                else:
                    successful += 1

            if progress_callback:
                total_processed = (batch_idx + 1) * len(batch)
                progress_callback(total_processed, len(batch) * (batch_idx + 1))

            return {"successful": successful, "failed": failed, "errors": errors}


class AsyncItemProcessor:
    def __init__(
        self,
        processor_func: Callable[[Any], Coroutine[Any, Any, Any]],
        config: Optional[BatchProcessingConfig] = None,
    ):
        self.processor_func = processor_func
        self.config = config or BatchProcessingConfig()
        self.batch_processor = AsyncBatchProcessor(self.config)

    async def process_items(
        self,
        items: List[Any],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> tuple[List[Any], BatchProcessingResult]:
        results: List[Any] = []

        async def process_item(item: Any) -> Any:
            return await self.processor_func(item)

        result = await self.batch_processor.process_batch(items, process_item, progress_callback)

        tasks = [process_item(item) for item in items]
        item_results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in item_results:
            if not isinstance(r, Exception):
                results.append(r)

        return results, result

    async def process_stream(
        self,
        item_stream: AsyncIterator[Any],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> tuple[List[Any], BatchProcessingResult]:
        batch: List[Any] = []
        all_results: List[Any] = []
        total_processed = 0
        successful = 0
        failed = 0
        errors: List[Dict[str, Any]] = []
        start_time = time.time()

        async for item in item_stream:
            batch.append(item)
            total_processed += 1
            if len(batch) >= self.config.batch_size:
                items_out, batch_result = await self.process_items(batch, progress_callback)
                all_results.extend(items_out)
                successful += batch_result.successful_items
                failed += batch_result.failed_items
                errors.extend(batch_result.errors)
                batch.clear()

        if batch:
            items_out, batch_result = await self.process_items(batch, progress_callback)
            all_results.extend(items_out)
            successful += batch_result.successful_items
            failed += batch_result.failed_items
            errors.extend(batch_result.errors)

        return all_results, BatchProcessingResult(
            total_items=total_processed,
            processed_items=total_processed,
            successful_items=successful,
            failed_items=failed,
            processing_time_seconds=time.time() - start_time,
            errors=errors,
        )
