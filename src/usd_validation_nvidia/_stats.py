# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

import collections
from collections.abc import Sequence
from enum import Enum, auto
from time import perf_counter_ns
from typing import Any, TypeVar

__all__ = [
    "ValidationStats",
]

_KeyType = tuple[Any, ...]
"""Alias for key type."""

_RuleType = TypeVar("_RuleType")
"""Alias for rule type."""


class _StatType(Enum):
    """
    Different type of statistics.
    """

    TIME = auto()
    COUNT = auto()


class _TimeStat:
    """A simple context manager to track time."""

    __slots__ = ("_key", "_stats", "_time")

    def __init__(self, stats: _Stats, key: tuple[Any, ...]):
        self._stats = stats
        self._key = key
        self._time: int | None = None

    def __enter__(self) -> None:
        self._time = perf_counter_ns()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._stats.add_stat(_StatType.TIME, self._key, perf_counter_ns() - self._time)


class _Stats:
    """
    A generic statistic implementation to keep track of times and counters.
    """

    def __init__(self):
        self._stats: dict[_KeyType, int] = collections.defaultdict(int)

    def clear(self) -> None:
        self._stats.clear()

    def add_stat(self, stat: _StatType, key: _KeyType, value: int | None = 1) -> None:
        self._stats[(stat, *key)] += value

    def get_stat(self, stat: _StatType, key: _KeyType) -> int:
        return self._stats[(stat, *key)]

    def get_stats(self, stat: _StatType, keys: Sequence[_KeyType]) -> list[tuple[_KeyType, int]]:
        key_set: set[_KeyType] = self._stats.keys() & set((stat, *key) for key in keys)
        return [(key[1:], self._stats[key]) for key in key_set]

    def time(self, key: tuple[Any, ...]) -> _TimeStat:
        return _TimeStat(self, key)


class ValidationStats(_Stats):
    """
    A specific implementation of statistics for validation. Apart from the generic methods, it includes:
    - add/get: A global counter.
    - time_rule: Measure the time spent executing a rule.
    - count_rule_severity: Keep track of rule, severity found in issues.
    """

    def __init__(self) -> None:
        super().__init__()
        self._time_rule: set[tuple[_RuleType]] = set()
        self._count_rule_severity: set[tuple[_RuleType, Enum]] = set()

    def time_rule(self, rule: _RuleType) -> _TimeStat:
        """Measure the time spent executing a rule."""
        self._time_rule.add((rule,))
        return self.time((rule,))

    def count_rule_severity(self, rule: _RuleType, severity: Enum) -> None:
        """Keep track of rule, severity found in issues."""
        self._count_rule_severity.add((rule, severity))
        self.add_stat(_StatType.COUNT, (severity,))
        self.add_stat(_StatType.COUNT, (rule, severity))

    def count_issues(self, issues) -> None:
        for issue in issues:
            self.count_rule_severity(issue.rule, issue.severity)

    def get_rule_times(self) -> list[tuple[_RuleType, float]]:
        return [(rule, (stat / 1e9)) for (rule,), stat in self.get_stats(_StatType.TIME, self._time_rule)]

    def total_time(self) -> float:
        """Returns the total time spent executing all rules, in seconds."""
        return sum(t for _, t in self.get_rule_times())

    def get_rule_severity_counts(self) -> list[tuple[_RuleType, Enum, int]]:
        return [
            (rule, severity, stat)
            for (rule, severity), stat in self.get_stats(_StatType.COUNT, self._count_rule_severity)
        ]

    def get_severity_count(self, severity: Enum) -> int:
        return self.get_stat(_StatType.COUNT, (severity,))
