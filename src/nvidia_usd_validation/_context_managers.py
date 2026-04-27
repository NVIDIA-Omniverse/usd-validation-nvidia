# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

import asyncio
from abc import abstractmethod
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from typing import Any

from pxr import UsdUtils

__all__ = [
    "MAXIMUM_BATCH_SIZE",
    "MAXIMUM_COUNT_SIZE",
    "AsyncBatchRunner",
    "AsyncCounter",
    "DelegateContextManager",
    "PeriodicCallback",
]

MAXIMUM_COUNT_SIZE: int = 1_024
"""Maximum number of objects to count per request."""

MAXIMUM_BATCH_SIZE: int = 256
"""Maximum number of events to process per request."""


@dataclass
class PeriodicCallback(AbstractAsyncContextManager):
    """Context manager class for invoking the given callback function periodically at a specified interval.

    Example:
        def my_callback():
            print("Callback function executed.")

        async with PeriodicCallback(my_callback, interval_seconds=2.0):
            await asyncio.sleep(10)  # Perform other tasks while the callback runs periodically

    Args:
        callback (callable): The callback function to be invoked periodically.
        interval_seconds (float): The interval duration in seconds at which the callback function should be invoked.
    """

    callback: Callable[[], None] | None
    interval_seconds: float = field(default=1.0)
    task: asyncio.Task | None = field(init=False, default=None)

    async def __aenter__(self) -> None:
        if self.callback is not None:
            await asyncio.to_thread(self.callback)
            self.task = asyncio.create_task(self._run())

    async def __aexit__(self, *_) -> None:
        if self.callback is not None:
            self.task.cancel()
            await asyncio.to_thread(self.callback)

    async def _run(self) -> None:
        while not self.task.done():
            await asyncio.sleep(self.interval_seconds)
            await asyncio.to_thread(self.callback)


@dataclass
class AsyncCounter(AbstractAsyncContextManager):
    """
    Count a (possibly) large number of objects in batches thus reducing time to schedule while also giving time
    for other threads/process to run.

    Example:
        async with AsyncCounter() as counter:
            await counter.count(object)
    """

    counter: int = field(init=False, default=0)

    async def __aexit__(self, *_) -> None: ...

    async def count(self, value: int) -> None:
        self.counter += value
        if self.counter % MAXIMUM_COUNT_SIZE == 0:
            await self._yield()

    async def _yield(self) -> None:
        # Explicitly move execution to a different thread to avoid blocking the main thread.
        await asyncio.to_thread(lambda: None)


@dataclass
class AsyncBatchRunner(AbstractAsyncContextManager):
    """
    Process a (possibly) large number of events in batches thus reducing time to schedule while also giving time
    for other threads/process to run.

    Example:
        async with AsyncBatchRunner() as runner:
            await runner.append(object)
    """

    counter: int = field(init=False, default=0)
    events: list[Any] = field(init=False, default_factory=list)

    async def __aexit__(self, *_) -> None:
        await self.flush()

    async def append(self, event: Any) -> None:
        self.events.append(event)
        self.counter += 1
        if len(self.events) == MAXIMUM_BATCH_SIZE:
            await self.flush()

    @abstractmethod
    def run(self, events) -> None:
        """Process all events in the batch."""
        ...

    async def flush(self) -> None:
        await asyncio.to_thread(self.run, self.events)
        self.events = []


@dataclass
class DelegateContextManager:
    """
    Context manager for CoalescingDiagnosticDelegate.

    Example:
        async with DelegateContextManager() as delegate:
            stage = Usd.Stage.CreateNew("path/to/stage.usd")
    """

    delegate: UsdUtils.CoalescingDiagnosticDelegate | None = None

    def __enter__(self) -> DelegateContextManager:
        self.delegate = UsdUtils.CoalescingDiagnosticDelegate()
        return self

    def __exit__(self, *_) -> None:
        self.delegate = None
