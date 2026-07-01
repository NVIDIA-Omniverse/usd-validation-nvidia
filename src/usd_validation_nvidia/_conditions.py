# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

import importlib
import logging
from collections.abc import Callable
from dataclasses import dataclass
from functools import cache
from typing import Protocol, runtime_checkable

__all__ = [
    "RulePredicate",
    "RulePredicates",
    "is_importable",
    "should_skip",
    "skip_if",
    "skip_unless",
]

_RULE_CONDITION_ATTR = "__usd_validation_nvidia_rule_condition__"
logger = logging.getLogger(__name__)


@runtime_checkable
class RulePredicate(Protocol):
    def __call__(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class _RuleCondition:
    predicate: RulePredicate
    reason: str

    def should_skip(self) -> bool:
        return bool(self.predicate())


class RulePredicates:
    @staticmethod
    def Create(condition: bool | RulePredicate) -> RulePredicate:
        if isinstance(condition, RulePredicate):
            return condition
        if isinstance(condition, bool):
            return lambda: condition
        raise TypeError("condition must be a bool or a callable returning bool.")

    @staticmethod
    def Not(condition: bool | RulePredicate) -> RulePredicate:
        predicate = RulePredicates.Create(condition)
        return lambda: not predicate()

    @staticmethod
    def IsImportable(module_name: str) -> RulePredicate:
        return is_importable(module_name)


def skip_if(condition: bool | RulePredicate, reason: str) -> Callable[[type], type]:
    """
    Decorate a validation rule so it is skipped at runtime when ``condition`` is true.

    Skipped rules remain registered and are reported as informational validation
    issues by the compliance checker. Use this for runtime support checks where
    the rule should be visible to users even when it cannot run.
    """
    if not isinstance(reason, str) or not reason:
        raise ValueError("reason must be a non-empty string.")

    predicate = RulePredicates.Create(condition)

    def decorator(rule_type: type) -> type:
        conditions = getattr(rule_type, _RULE_CONDITION_ATTR, ())
        setattr(
            rule_type,
            _RULE_CONDITION_ATTR,
            (
                *conditions,
                _RuleCondition(predicate=predicate, reason=reason),
            ),
        )
        return rule_type

    return decorator


def skip_unless(condition: bool | RulePredicate, reason: str) -> Callable[[type], type]:
    """
    Decorate a validation rule so it is skipped at runtime unless ``condition`` is true.

    Skipped rules remain registered and are reported as informational validation
    issues by the compliance checker. Use this for runtime support checks where
    the rule should be visible to users even when it cannot run.
    """
    return skip_if(RulePredicates.Not(condition), reason=reason)


@cache
def is_importable(module_name: str) -> RulePredicate:
    """
    Return a cached predicate that checks whether ``module_name`` can be imported.

    This helper imports the module instead of only checking for a module spec,
    because optional schema packages can be discoverable while still failing to
    load due to missing native dependencies.
    """

    def predicate() -> bool:
        try:
            importlib.import_module(module_name)
        except ImportError:
            return False
        return True

    return predicate


def should_skip(rule_type: type) -> str | None:
    """
    Return the rule skip reason for ``rule_type``, or ``None`` when it should run.
    """
    for condition in getattr(rule_type, _RULE_CONDITION_ATTR, ()):
        try:
            if condition.should_skip():
                return condition.reason
        except Exception as error:
            logger.exception(f"Failed to evaluate rule condition for rule {rule_type.__name__}")
            return f"Failed to evaluate rule condition: {error}"
    return None
