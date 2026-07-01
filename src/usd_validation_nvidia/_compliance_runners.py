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
from dataclasses import InitVar, dataclass, field
from enum import Enum
from inspect import iscoroutinefunction
from operator import attrgetter
from typing import Any, Generic, TypeVar, cast

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
    FORMAT_DEPENDENCY = attrgetter(BaseRuleChecker.CheckFormatDependency.__name__)
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
            or (
                self.type is ComplianceCheckerEventType.FORMAT_DEPENDENCY
                and not self.metadata.is_format_dependency_implemented()
            )
        )

    def is_heavy_task(self) -> bool:
        return (
            (self.type is ComplianceCheckerEventType.STAGE and self.metadata.is_only_stage_implemented())
            or (self.type is ComplianceCheckerEventType.LAYER and self.metadata.is_only_layer_implemented())
            or (self.type is ComplianceCheckerEventType.ZIP_FILE and self.metadata.is_only_zip_implemented())
            or (
                self.type is ComplianceCheckerEventType.FORMAT_DEPENDENCY
                and self.metadata.is_only_format_dependency_implemented()
            )
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
class AbstractRunner(Generic[T]):
    stats: ValidationStats
    counter: int = field(init=False, default=0)
    events: list[T] = field(init=False, default_factory=list)
    context: Ar.Context = field(init=False, default_factory=lambda: Ar.GetResolver().GetCurrentContext())

    def accepts(self, event_rule: ComplianceCheckerEventRule) -> bool:
        return False

    def map(self, event_rule: ComplianceCheckerEventRule) -> T:
        return cast(T, event_rule)

    def pop(self) -> list[T]:
        events: list[T] = self.events
        self.events = []
        return events


@dataclass
class AbstractSyncRunner(AbstractRunner[T]):
    def submit(self, event_rule: ComplianceCheckerEventRule) -> None:
        self.events.append(self.map(event_rule))
        if len(self.events) == MAXIMUM_BATCH_SIZE:
            self.flush()

    def flush(self) -> None: ...

    def close(self) -> None:
        self.flush()


@dataclass
class AbstractAsyncRunner(AbstractRunner[T]):
    async def submit_async(self, event_rule: ComplianceCheckerEventRule) -> None:
        self.events.append(self.map(event_rule))
        if len(self.events) == MAXIMUM_BATCH_SIZE:
            await self.flush_async()

    async def flush_async(self) -> None: ...

    async def close_async(self) -> None:
        await self.flush_async()


@dataclass
class SyncNoopRunner(AbstractSyncRunner[ComplianceCheckerEventRule]):
    """Counts empty rule-event pairs without running work."""

    def accepts(self, event_rule: ComplianceCheckerEventRule) -> bool:
        return event_rule.is_empty_task()

    def submit(self, event_rule: ComplianceCheckerEventRule) -> None:
        self.counter += 1


@dataclass
class SyncInlineRunner(AbstractSyncRunner[ComplianceCheckerEventRule]):
    """Runs sync events inline on the current thread."""

    def accepts(self, event_rule: ComplianceCheckerEventRule) -> bool:
        return not event_rule.is_async_task()

    def flush(self) -> None:
        if not self.events:
            return
        with Ar.ResolverContextBinder(self.context):
            with Ar.ResolverScopedCache():
                events: list[ComplianceCheckerEventRule] = self.pop()
                for event in events:
                    event.apply(self.stats)
                self.counter += len(events)


@dataclass
class SyncCoroutineRunner(AbstractSyncRunner[Awaitable[None]]):
    """Runs coroutine events from synchronous code."""

    def accepts(self, event_rule: ComplianceCheckerEventRule) -> bool:
        return event_rule.is_async_task()

    def map(self, event_rule: ComplianceCheckerEventRule) -> Awaitable[None]:
        return event_rule.applyAsync(self.stats)

    def flush(self) -> None:
        if not self.events:
            return
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._flush_async())
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(asyncio.run, self._flush_async()).result()

    async def _flush_async(self) -> None:
        events: list[Awaitable[None]] = self.pop()
        await asyncio.gather(*events)
        self.counter += len(events)


@dataclass
class AsyncNoopRunner(AbstractAsyncRunner[ComplianceCheckerEventRule]):
    """Counts empty rule-event pairs without running work."""

    def accepts(self, event_rule: ComplianceCheckerEventRule) -> bool:
        return event_rule.is_empty_task()

    async def submit_async(self, event_rule: ComplianceCheckerEventRule) -> None:
        self.counter += 1


@dataclass
class AsyncCoroutineRunner(AbstractAsyncRunner[ComplianceCheckerEventRule]):
    """Runs coroutine events during async flush."""

    def accepts(self, event_rule: ComplianceCheckerEventRule) -> bool:
        return not event_rule.is_heavy_task() and event_rule.is_async_task()

    async def flush_async(self) -> None:
        if not self.events:
            return
        with Ar.ResolverContextBinder(self.context):
            with Ar.ResolverScopedCache():
                events: list[ComplianceCheckerEventRule] = self.pop()
                for event in events:
                    await event.applyAsync(self.stats)
                self.counter += len(events)


@dataclass
class AsyncThreadRunner(AbstractAsyncRunner[ComplianceCheckerEventRule]):
    """Runs sync events in a thread pool."""

    pool: ThreadPoolExecutor = field(init=False, default_factory=ThreadPoolExecutor)

    def accepts(self, event_rule: ComplianceCheckerEventRule) -> bool:
        return not event_rule.is_async_task() and not event_rule.is_heavy_task()

    def _flush_sync(self) -> None:
        with Ar.ResolverContextBinder(self.context):
            with Ar.ResolverScopedCache():
                events: list[ComplianceCheckerEventRule] = self.pop()
                for event in events:
                    event.apply(self.stats)
                self.counter += len(events)

    async def flush_async(self) -> None:
        if not self.events:
            return
        loop: AbstractEventLoop = asyncio.get_running_loop()
        ctx: ContextVar = contextvars.copy_context()
        func: Callable[[], None] = functools.partial(ctx.run, self._flush_sync)
        await loop.run_in_executor(self.pool, func)


@dataclass
class AsyncCoroutineTaskRunner(AbstractAsyncRunner[asyncio.Task]):
    """Starts coroutine events during async submit."""

    def accepts(self, event_rule: ComplianceCheckerEventRule) -> bool:
        return event_rule.is_heavy_task() and event_rule.is_async_task()

    async def _run(self, event_rule: ComplianceCheckerEventRule) -> None:
        with Ar.ResolverContextBinder(self.context):
            with Ar.ResolverScopedCache():
                await event_rule.applyAsync(self.stats)

    def map(self, event_rule: ComplianceCheckerEventRule) -> asyncio.Task:
        return asyncio.create_task(self._run(event_rule))

    async def flush_async(self) -> None:
        if not self.events:
            return
        tasks: list[asyncio.Task] = self.pop()
        await asyncio.gather(*tasks)
        self.counter += len(tasks)


@dataclass
class AsyncThreadTaskRunner(AbstractAsyncRunner[asyncio.Task]):
    """Starts sync events in a thread during async submit."""

    pool: ThreadPoolExecutor = field(init=False, default_factory=ThreadPoolExecutor)

    def accepts(self, event_rule: ComplianceCheckerEventRule) -> bool:
        return event_rule.is_heavy_task() and not event_rule.is_async_task()

    def _run(self, event_rule: ComplianceCheckerEventRule) -> None:
        with Ar.ResolverContextBinder(self.context):
            with Ar.ResolverScopedCache():
                event_rule.apply(self.stats)

    async def _run_async(self, event_rule: ComplianceCheckerEventRule) -> None:
        loop: AbstractEventLoop = asyncio.get_running_loop()
        ctx: ContextVar = contextvars.copy_context()
        func: Callable[[], None] = functools.partial(ctx.run, self._run, event_rule)
        await loop.run_in_executor(self.pool, func)

    def map(self, event_rule: ComplianceCheckerEventRule) -> asyncio.Task:
        return asyncio.create_task(self._run_async(event_rule))

    async def flush_async(self) -> None:
        if not self.events:
            return
        tasks: list[asyncio.Task] = self.pop()
        await asyncio.gather(*tasks)
        self.counter += len(tasks)


@dataclass
class SyncComplianceCheckerRunner(AbstractContextManager):
    """
    A runner for compliance checker events.
    """

    rules: list[BaseRuleChecker]
    stats: InitVar[ValidationStats]
    runners: list[AbstractSyncRunner[Any]] = field(init=False)

    def __post_init__(self, stats: ValidationStats) -> None:
        self.runners = [
            SyncNoopRunner(stats),
            SyncInlineRunner(stats),
            SyncCoroutineRunner(stats),
        ]

    def __exit__(self, *_) -> None:
        self.flush()

    def append(self, event: ComplianceCheckerEvent) -> None:
        if event.type is ComplianceCheckerEventType.FLUSH:
            self.flush()
            return
        for rule in self.rules:
            event_rule = ComplianceCheckerEventRule(event, rule)
            for runner in self.runners:
                if runner.accepts(event_rule):
                    runner.submit(event_rule)
                    break

    def flush(self) -> None:
        for runner in self.runners:
            runner.flush()


@dataclass
class AsyncComplianceCheckerRunner(AbstractAsyncContextManager):
    """
    A runner for compliance checker events. It has a mixed strategy:
    - Long running events are immediately triggered in a background thread.
    - Short running events are accumulated in a batch and then flushed to the background thread.
    """

    rules: list[BaseRuleChecker]
    stats: InitVar[ValidationStats]
    runners: list[AbstractAsyncRunner[Any]] = field(init=False)

    def __post_init__(self, stats: ValidationStats) -> None:
        self.runners = [
            AsyncNoopRunner(stats),
            AsyncCoroutineRunner(stats),
            AsyncThreadRunner(stats),
            AsyncCoroutineTaskRunner(stats),
            AsyncThreadTaskRunner(stats),
        ]

    @property
    def counter(self) -> int:
        return sum(runner.counter for runner in self.runners)

    async def __aexit__(self, *_) -> None:
        await self.flush()

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
            for runner in self.runners:
                if runner.accepts(event_rule):
                    await runner.submit_async(event_rule)
                    break

    async def flush(self) -> None:
        await asyncio.gather(*(runner.flush_async() for runner in self.runners))
