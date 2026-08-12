# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

__all__ = [
    "is_multiprocess_safe",
    "multiprocess_safe",
]


F = TypeVar("F", bound=Callable[..., Any])
_MULTIPROCESS_SAFE_ATTR = "__usd_validation_nvidia_multiprocess_safe__"


def multiprocess_safe(method: F) -> F:
    """Decorator. Mark a rule method as safe to run in a process pool (if enabled).

    .. code-block:: python

        from usd_validation_nvidia import BaseRuleChecker, multiprocess_safe

        class MyRule(BaseRuleChecker):
            @multiprocess_safe
            def CheckLayer(self, layer):
                ...
    """
    setattr(method, _MULTIPROCESS_SAFE_ATTR, True)
    return method


def is_multiprocess_safe(method: Callable[..., Any]) -> bool:
    """Return whether ``method`` is marked safe to run in a process pool.

    This is the public companion predicate for :py:func:`multiprocess_safe`.

    Args:
        method: Rule method to inspect.

    Returns:
        True when ``method`` was decorated with :py:func:`multiprocess_safe`, false otherwise.
    """
    return bool(getattr(method, _MULTIPROCESS_SAFE_ATTR, False))
