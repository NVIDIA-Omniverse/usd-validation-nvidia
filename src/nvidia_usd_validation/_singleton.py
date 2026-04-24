# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from functools import cache
from typing import TypeVar

__all__ = ["singleton"]

_T = TypeVar("_T")


def singleton(cls: type[_T]) -> type[_T]:
    """
    Decorator that creates a singleton class.

    Like applying ``@functools.cache`` to a class, but does not expose
    ``cache_clear()``. To manage singleton state use the class's own
    ``add()``, ``remove()``, or ``clear()`` methods instead.

    Example::

        @singleton
        class MyRegistry(VersionedRegistry[MyType]):
            def __init__(self):
                super().__init__()
    """
    cached = cache(cls)

    def _no_cache_clear() -> None:
        raise AttributeError(f"'{cls.__name__}' object has no attribute 'cache_clear'")

    cached.cache_clear = _no_cache_clear
    return cached  # type: ignore[return-value]
