# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cached_property
from typing import Protocol, runtime_checkable

from .utils import (
    EventListener,
    EventStream,
    UriResolver,
    create_event_stream,
    singleton,
)

__all__ = [
    "AssetFormat",
    "AssetFormatRegistry",
    "FormatDependency",
    "add_registry_asset_format_callback",
    "register_format",
    "unregister_format",
]


@dataclass(frozen=True)
class FormatDependency:
    """Context object passed to :py:meth:`~usd_validation_nvidia.BaseRuleChecker.CheckFormatDependency`.

    Attributes:
        path: The specific dependency path being checked.
        uri_resolver: For URI operations: listing files, joining paths, checking existence.
        root_asset_path: The top-level asset that initiated this dependency chain.
    """

    path: str
    uri_resolver: UriResolver = field(repr=False)
    root_asset_path: str


@runtime_checkable
class AssetFormat(Protocol):
    """Protocol for non-USD asset format handlers.

    Implementations identify and extract dependencies for a specific asset
    format. The compliance checker queries :py:class:`AssetFormatRegistry` to
    find the right handler before dispatching ``CheckArAsset`` to rules.
    """

    def supports(self, asset_path: str) -> bool:
        """Check if this handler understands the given asset.

        Args:
            asset_path: Path or URI of the asset to inspect.

        Returns:
            True if this handler can process *asset_path*, False otherwise.
        """
        ...

    def get_dependencies(self, asset_path: str, uri_resolver: UriResolver) -> list[str]:
        """Return all paths reachable from the asset at *asset_path*.

        The asset itself must be the first element of the returned list.
        For hierarchical formats (e.g. bundle manifests that reference child
        manifests) implementations should recurse and return the complete flat
        list, so callers collect every file in the hierarchy — internal nodes
        and leaf assets alike — in a single call.

        Args:
            asset_path: Path or URI of the asset to inspect.
            uri_resolver: Used for URI manipulation (parent directory, path
                joining). Use ``Ar.GetResolver()`` inside the implementation
                for reading file content — those are distinct concerns.

        Returns:
            Flat list of all paths in the hierarchy, with *asset_path* first.
        """
        ...


@singleton
class AssetFormatRegistry:
    """Singleton registry of :py:class:`AssetFormat` handlers.

    Handlers are queried in registration order; the first one whose
    :py:meth:`AssetFormat.supports` returns ``True`` is used.
    """

    def __init__(self) -> None:
        self._formats: dict[type[AssetFormat], AssetFormat] = {}

    @cached_property
    def event_stream(self) -> EventStream:
        return create_event_stream()

    def add(self, fmt_class: type[AssetFormat]) -> None:
        instance = fmt_class()
        if not isinstance(instance, AssetFormat):
            raise TypeError(f"{fmt_class.__name__} does not implement the AssetFormat protocol")
        self._formats[fmt_class] = instance
        self.event_stream.notify()

    def remove(self, fmt_class: type[AssetFormat]) -> None:
        del self._formats[fmt_class]
        self.event_stream.notify()

    def clear(self) -> None:
        self._formats.clear()
        self.event_stream.notify()

    def find(self, asset_path: str) -> AssetFormat | None:
        for fmt in self._formats.values():
            if fmt.supports(asset_path):
                return fmt
        return None

    def add_callback(self, callback: Callable[[], None]) -> EventListener:
        return self.event_stream.create_event_listener(callback)


def register_format() -> Callable[[type[AssetFormat]], type[AssetFormat]]:
    """Decorator. Register an :py:class:`AssetFormat` handler class.

    .. code-block:: python

        @register_format()
        class MyFormat:
            def supports(self, asset_path: str) -> bool: ...
            def get_dependencies(self, asset_path: str, uri_resolver: UriResolver) -> list[str]: ...
    """

    def _register(fmt_class: type[AssetFormat]) -> type[AssetFormat]:
        AssetFormatRegistry().add(fmt_class)
        return fmt_class

    return _register


def unregister_format(fmt_class: type[AssetFormat]) -> None:
    """Unregister an :py:class:`AssetFormat` handler by class."""
    AssetFormatRegistry().remove(fmt_class)


def add_registry_asset_format_callback(callback: Callable[[], None]) -> EventListener:
    """Subscribe *callback* to :py:class:`AssetFormatRegistry` change events."""
    return AssetFormatRegistry().add_callback(callback)
