# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any, Protocol, TypeVar, runtime_checkable

from ._registry import IdVersion, VersionedRegistry
from .capabilities import RequirementProtocol, RequirementRefProtocol
from .utils import EventListener, SemVer, deprecated, singleton

__all__ = [
    "Requirement",
    "RequirementsRegistry",
    "add_registry_requirement_callback",
    "register_requirements",
    "unregister_requirements",
]

# TypeVar for BaseRuleChecker to avoid circular import
BaseRuleChecker = TypeVar("BaseRuleChecker")


@runtime_checkable
class _RequirementLikeProtocol(Protocol):
    """
    A minimal concrete requirement shape accepted by register_requirements.
    """

    code: str
    version: str | None
    display_name: str | None
    message: str | None
    path: str | None
    tags: tuple[str, ...]
    parameters: tuple[Any, ...]
    examples: tuple[Any, ...]


Requirement = RequirementProtocol
""" Left for backwards compatibility. """


@singleton
class RequirementsRegistry(VersionedRegistry[Requirement]):
    """
    A singleton class that keeps requirements and maps them to rules.
    """

    def __init__(self):
        super().__init__()
        self._req_to_rule: dict[IdVersion, list[type[BaseRuleChecker]]] = defaultdict(list)
        self._rule_to_req: dict[type[BaseRuleChecker], list[Requirement]] = defaultdict(list)

    def create_key(self, value: Requirement | RequirementRefProtocol) -> IdVersion:
        return IdVersion(value.code, SemVer(value.version))

    @property
    @deprecated("Iterate over the registry instead")
    def requirements(self) -> list[Requirement]:
        """
        Returns:
            The list of registered requirements.
        """
        # Get requirements from versioned registry
        return list(self)

    @property
    def latest_requirements(self) -> list[Requirement]:
        """Get only the latest version of each requirement."""
        return self.latest_values()

    @property
    def rules(self):
        """
        Returns:
            The list of rules mapped to the registered requirements.
        """
        return list(self._rule_to_req.keys())

    def clear(self) -> None:
        self._req_to_rule.clear()
        self._rule_to_req.clear()
        super().clear()

    def _add_validator_requirements(
        self, rule: type[BaseRuleChecker], requirements: list[Requirement], override: bool = False
    ) -> None:
        for requirement in requirements:
            if not isinstance(requirement, _RequirementLikeProtocol):
                raise TypeError("register_requirements expects concrete Requirement objects.")

        with self.event_stream:
            for requirement in requirements:
                if not override and self.is_implemented(requirement):
                    raise ValueError(f"Requirement {requirement} already declared in {self.get_validator(requirement)}")
                key = self.create_key(requirement)
                if not self._req_to_rule[key]:
                    self.add(requirement)
                self._req_to_rule[key].append(rule)
                self._rule_to_req[rule].append(requirement)

    def _remove_validator_requirements(self, rule: type[BaseRuleChecker]) -> None:
        with self.event_stream:
            # Iterate the rule's actual registrations (snapshot copy because we mutate
            # during iteration). ``get_requirements`` only returns primary registrations,
            # so using it here would leak non-primary entries when the rule had been
            # overridden by another rule on the same requirement (OMPE-64259).
            for requirement in list(self._rule_to_req[rule]):
                key = self.create_key(requirement)
                self._req_to_rule[key].remove(rule)
                self._rule_to_req[rule].remove(requirement)
                if not self._req_to_rule[key]:
                    del self[key]

    def get_requirements(self, rule: type[BaseRuleChecker]) -> list[Requirement]:
        """
        Returns the requirements that the rule validates.

        Args:
            rule: A validator rule.

        Returns:
            The list of requirements that the rule validates.
        """
        requirements: list[Requirement] = []
        for requirement in self._rule_to_req[rule]:
            if self.get_validator(requirement) == rule:
                requirements.append(requirement)
        return requirements

    def resolve_requirement(
        self, requirement: Requirement | RequirementRefProtocol
    ) -> Requirement | RequirementRefProtocol:
        """
        Resolve a requirement reference to a registered requirement when possible.

        Args:
            requirement: A concrete requirement or a reference to a requirement.

        Returns:
            A requirement if found in the registry, otherwise the reference itself.
        """
        if isinstance(requirement, RequirementProtocol):
            return requirement
        return self.find_requirement(requirement.code, requirement.version) or requirement

    def resolve_requirements(
        self, requirements: list[Requirement | RequirementRefProtocol]
    ) -> list[Requirement | RequirementRefProtocol]:
        """
        Resolve requirement references to registered requirements when possible.

        Args:
            requirements: Concrete requirements or references to requirements.

        Returns:
            Requirements found in the registry, otherwise the original references.
        """
        return [self.resolve_requirement(requirement) for requirement in requirements]

    def get_validator(self, requirement: Requirement | RequirementRefProtocol) -> type[BaseRuleChecker] | None:
        """
        Returns the last registered validator for the requirement.

        Args:
            requirement: A requirement.

        Returns:
            The last registered validator for the requirement or None.
        """
        requirement = self.resolve_requirement(requirement)
        key = self.create_key(requirement)
        rules: list[type[BaseRuleChecker]] = self._req_to_rule[key]
        if not rules:
            return None
        return rules[-1]

    def get_validators(self, requirements: list[Requirement | RequirementRefProtocol]) -> list[type[BaseRuleChecker]]:
        """
        Args:
            requirements: The list of requirements.

        Returns:
            The list of rules implementing all requirements.
        """
        rules: set[type[BaseRuleChecker]] = set()
        for requirement in requirements:
            if validator := self.get_validator(requirement):
                rules.add(validator)
        return list(rules)

    def is_implemented(self, requirement: Requirement | RequirementRefProtocol) -> bool:
        """
        Args:
            requirement: A requirement.

        Returns:
            True if the requirement is implemented.
        """
        return self.get_validator(requirement) is not None

    def all_implemented(self, requirements: list[Requirement | RequirementRefProtocol]) -> bool:
        """
        Args:
            requirements: The list of requirements.

        Returns:
            True if all requirements are implemented.
        """
        return all(map(self.is_implemented, requirements))

    def is_registered(self, rule: type[BaseRuleChecker], requirement: Requirement | RequirementRefProtocol) -> bool:
        """
        Returns True if the rule is registered to the requirement, regardless of
        whether it is the primary (last-registered) validator. Use
        :py:meth:`get_validator` to check primary status.

        Args:
            rule: A rule.
            requirement: A requirement.

        Returns:
            True if the rule is registered to the requirement.
        """
        requirement = self.resolve_requirement(requirement)
        key = self.create_key(requirement)
        return rule in self._req_to_rule[key]

    def find_requirement(self, code: str, version: str | None = None) -> Requirement | None:
        """
        Find a requirement by code and version.

        Args:
            code: The requirement code
            version: The version to find, defaults to latest

        Returns:
            The requirement if found, None otherwise
        """
        return self.find(code, version)

    def __delitem__(self, key: IdVersion) -> None:
        requirement: Requirement = self[key]
        for rule in list(self._req_to_rule.pop(key)):
            self._rule_to_req[rule].remove(requirement)
        super().__delitem__(key)


def register_requirements(
    *requirements: Requirement, override: bool = False
) -> Callable[[type[BaseRuleChecker]], type[BaseRuleChecker]]:
    """Decorator. Register a new :py:class:`BaseRuleChecker` to a set of requirements.

    .. code-block:: python

        @register_requirements(Requirement1, Requirement2)
        class MyRule(BaseRuleChecker):
            ...

    To override a registered rule, use the ``override`` parameter.

    .. code-block:: python

        @register_requirements(Requirement1, override=True)
        class MyRule(BaseRuleChecker):
            ...
    """

    def _register_requirements(rule_class: type[BaseRuleChecker]) -> type[BaseRuleChecker]:
        RequirementsRegistry()._add_validator_requirements(rule_class, list(requirements), override=override)
        return rule_class

    return _register_requirements


def unregister_requirements(
    rule: type[BaseRuleChecker],
) -> None:
    """
    Unregister a rule from all requirements.

    Args:
        rule: The rule to unregister.

    Example:

    .. code-block:: python

        @register_requirements(Requirement1, Requirement2)
        class MyRule(BaseRuleChecker):
            ...

        unregister_requirements(MyRule)
    """
    RequirementsRegistry()._remove_validator_requirements(rule)


def add_registry_requirement_callback(callback: Callable[[], None]) -> EventListener:
    """
    Add a callback to be called when a requirement is registered or deregistered.
    Returns a subscription object that can be used to unsubscribe.

    Example:

    .. code-block:: python

        subscription = add_registry_requirement_callback(lambda: print("Requirement registered"))

        @register_requirements(Requirement1, Requirement2)
        class MyRule(BaseRuleChecker):
            ...

    Args:
        callback: A callback to be called when a requirement is registered or deregistered.

    Returns:
        A subscription object that can be used to unsubscribe.
    """
    return RequirementsRegistry().add_callback(callback)
