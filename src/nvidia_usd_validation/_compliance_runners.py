# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

import asyncio
import contextvars
import functools
from asyncio import AbstractEventLoop
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import Enum
from inspect import iscoroutinefunction
from operator import attrgetter
from typing import Any, Generic, TypeVar

from pxr import Ar

from ._base_rule_checker import BaseRuleChecker
from ._base_rule_metadata import BaseRuleCheckerMetadata
from ._context_managers import MAXIMUM_BATCH_SIZE
from ._stats import ValidationStats

__all__ = [
    "AsyncComplianceCheckerRunner",
    "ComplianceCheckerEvent",
    "ComplianceCheckerEventType",
    "SyncComplianceCheckerRunner",
]


T = TypeVar("T")


class ComplianceCheckerEventType(Enum):
    """A type of event in compliance checker."""

    STAGE = attrgetter(BaseRuleChecker.CheckStage.__name__)
    DIAGNOSTICS = attrgetter(BaseRuleChecker.CheckDiagnostics.__name__)
    UNRESOLVED_PATHS = attrgetter(BaseRuleChecker.CheckUnresolvedPaths.__name__)
    DEPENDENCIES = attrgetter(BaseRuleChecker.CheckDependencies.__name__)
    LAYER = attrgetter(BaseRuleChecker.CheckLayer.__name__)
    ZIP_FILE = attrgetter(BaseRuleChecker.CheckZipFile.__name__)
    PRIM = attrgetter(BaseRuleChecker.CheckPrim.__name__)
    RESET_CACHE = attrgetter(BaseRuleChecker.ResetCaches.__name__)
    FLUSH = None

    def apply(self, rule: BaseRuleChecker, args: tuple[Any, ...]) -> None:
        try:
            func: Callable[..., None] = self.value(rule)
            func(*args)
        except Exception as error:
            rule._AddError(message=f"Uncaught error: {error}")

    async def applyAsync(self, rule: BaseRuleChecker, args: tuple[Any, ...]) -> None:
        try:
            func: Callable[..., Awaitable[None]] = self.value(rule)
            await func(*args)
        except Exception as error:
            rule._AddError(message=f"Uncaught error: {error}")


@dataclass(frozen=True, slots=True)
class ComplianceCheckerEvent:
    """A compliance checker event."""

    type: ComplianceCheckerEventType
    value: None | Any | tuple[Any, ...]

    @property
    def args(self) -> tuple[Any, ...]:
        if self.value is None:
            return ()
        elif isinstance(self.value, tuple):
            return self.value
        else:
            return (self.value,)

    def apply(self, rules: list[BaseRuleChecker], stats: ValidationStats) -> None:
        for rule in rules:
            with stats.time_rule(rule.__class__):
                self.type.apply(rule, self.args)


@dataclass(frozen=True, slots=True)
class ComplianceCheckerEventRule:
    """A compliance checker event for a rule."""

    event: ComplianceCheckerEvent
    rule: BaseRuleChecker

    @property
    def type(self) -> ComplianceCheckerEventType:
        return self.event.type

    @property
    def metadata(self) -> BaseRuleCheckerMetadata:
        return BaseRuleCheckerMetadata(type(self.rule))

    def is_empty_task(self) -> bool:
        return (
            (self.type is ComplianceCheckerEventType.STAGE and not self.metadata.is_stage_implemented())
            or (self.type is ComplianceCheckerEventType.LAYER and not self.metadata.is_layer_implemented())
            or (self.type is ComplianceCheckerEventType.ZIP_FILE and not self.metadata.is_zip_implemented())
            or (self.type is ComplianceCheckerEventType.PRIM and not self.metadata.is_prim_implemented())
        )

    def is_heavy_task(self) -> bool:
        return (
            (self.type is ComplianceCheckerEventType.STAGE and self.metadata.is_only_stage_implemented())
            or (self.type is ComplianceCheckerEventType.LAYER and self.metadata.is_only_layer_implemented())
            or (self.type is ComplianceCheckerEventType.ZIP_FILE and self.metadata.is_only_zip_implemented())
        )

    def is_async_task(self) -> bool:
        method: Callable[..., None] | Callable[..., Awaitable[None]] = self.type.value(self.rule)
        return iscoroutinefunction(method)

    def apply(self, stats: ValidationStats) -> None:
        with stats.time_rule(self.rule.__class__):
            self.type.apply(self.rule, self.event.args)

    async def applyAsync(self, stats: ValidationStats) -> None:
        with stats.time_rule(self.rule.__class__):
            await self.type.applyAsync(self.rule, self.event.args)


@dataclass
class SyncComplianceCheckerRunner(AbstractContextManager):
    """
    A runner for compliance checker events.
    """

    rules: list[BaseRuleChecker]
    stats: ValidationStats
    tasks: list[Awaitable[None]] = field(init=False, default_factory=list)

    def __exit__(self, *_) -> None:
        self.flush()

    def append(self, event: ComplianceCheckerEvent) -> None:
        if event.type is ComplianceCheckerEventType.FLUSH:
            self.flush()
            return
        for rule in self.rules:
            event_rule = ComplianceCheckerEventRule(event, rule)
            if event_rule.is_empty_task():
                continue
            elif event_rule.is_async_task():
                self.tasks.append(event_rule.applyAsync(self.stats))
            else:
                event_rule.apply(self.stats)

    async def runAsync(self) -> None:
        await asyncio.gather(*self.tasks)

    def flush(self) -> None:
        if not self.tasks:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        try:
            if loop is None:
                asyncio.run(self.runAsync())
            else:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(asyncio.run, self.runAsync())
                    future.result()
        finally:
            self.tasks.clear()


@dataclass
class AsyncBatch(Generic[T]):
    flush_fn: Callable[[list[T]], Awaitable[None]]
    items: list[T] = field(init=False, default_factory=list)

    async def append(self, item: T) -> None:
        self.items.append(item)
        if len(self.items) == MAXIMUM_BATCH_SIZE:
            await self.flush()

    async def flush(self) -> None:
        if self.items:
            items: list[T] = self.items
            self.items = []
            await self.flush_fn(items)


@dataclass
class AsyncComplianceCheckerRunner(AbstractAsyncContextManager):
    """
    A runner for compliance checker events. It has a mixed strategy:
    - Long running events are immediately triggered in a background thread.
    - Short running events are accumulated in a batch and then flushed to the background thread.
    """

    rules: list[BaseRuleChecker]
    stats: ValidationStats
    counter: int = field(init=False, default=0)
    _sync_batch: AsyncBatch[ComplianceCheckerEventRule] = field(init=False)
    _async_batch: AsyncBatch[ComplianceCheckerEventRule] = field(init=False)
    _pool: ThreadPoolExecutor = field(init=False, default_factory=ThreadPoolExecutor)
    _tasks: set[asyncio.Task] = field(init=False, default_factory=set)
    _ctx: Ar.Context = field(init=False, default_factory=lambda: Ar.GetResolver().GetCurrentContext())

    def __post_init__(self) -> None:
        self._sync_batch = AsyncBatch(functools.partial(self._flush, self._runSync))
        self._async_batch = AsyncBatch(functools.partial(self._flush, self.runAsync))

    async def __aexit__(self, *_) -> None:
        await self.flush()
        await asyncio.gather(*self._tasks)
        while self._tasks:  # wait callbacks to be executed
            await asyncio.sleep(0)

    async def append(self, event: ComplianceCheckerEvent) -> None:
        """
        Appends an event

        Args:
            event (ComplianceCheckerEvent): The event to be appended.
        """
        if event.type is ComplianceCheckerEventType.FLUSH:
            await self.flush()
            return
        for rule in self.rules:
            event_rule = ComplianceCheckerEventRule(event, rule)
            if event_rule.is_empty_task():
                self.counter += 1
            elif event_rule.is_heavy_task():
                await self._trigger(event_rule)
            else:
                await self._schedule(event_rule)

    async def _trigger(self, event: ComplianceCheckerEventRule) -> None:
        """
        Trigger the event to be executed in a background thread.

        Args:
            event (ComplianceCheckerEventRule): The event to be executed.
        """

        def done_callback(task: asyncio.Task) -> None:
            self._tasks.discard(task)
            self.counter += 1

        if event.is_async_task():
            task = asyncio.create_task(self.runAsync([event]))
        else:
            task = asyncio.create_task(self._runSync([event]))
        self._tasks.add(task)
        task.add_done_callback(done_callback)

    async def _schedule(self, event: ComplianceCheckerEventRule) -> None:
        """
        Schedule the event to be executed in a batch.

        Args:
            event (ComplianceCheckerEventRule): The event to be executed.
        """
        if event.is_async_task():
            await self._async_batch.append(event)
        else:
            await self._sync_batch.append(event)

    async def _runSync(self, events: list[ComplianceCheckerEventRule]):
        """
        This is the same as asyncio.to_thread, but we use our own pool instead of the default one.

        Args:
            events (list[ComplianceCheckerEventRule]): The events to be executed.
        """
        loop: AbstractEventLoop = asyncio.get_running_loop()
        ctx: ContextVar = contextvars.copy_context()
        func: Callable[[], None] = functools.partial(ctx.run, self.run, events)
        return await loop.run_in_executor(self._pool, func)

    async def _flush(
        self,
        run_fn: Callable[[list[ComplianceCheckerEventRule]], Awaitable[None]],
        events: list[ComplianceCheckerEventRule],
    ) -> None:
        """
        Flush events using the given run function and increment counter.

        Args:
            run_fn (Callable): The function to run the events (either _runSync or runAsync).
            events (list[ComplianceCheckerEventRule]): The events to be executed.
        """
        await run_fn(events)
        self.counter += len(events)

    async def flush(self) -> None:
        await asyncio.gather(self._sync_batch.flush(), self._async_batch.flush())

    def run(self, events: list[ComplianceCheckerEventRule]) -> None:
        with Ar.ResolverContextBinder(self._ctx):
            with Ar.ResolverScopedCache():
                for event in events:
                    event.apply(self.stats)

    async def runAsync(self, events: list[ComplianceCheckerEventRule]) -> None:
        with Ar.ResolverContextBinder(self._ctx):
            with Ar.ResolverScopedCache():
                for event in events:
                    await event.applyAsync(self.stats)
