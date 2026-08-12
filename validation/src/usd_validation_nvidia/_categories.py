# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from collections.abc import Callable, Sequence
from functools import cache

from ._base_rule_checker import BaseRuleChecker
from ._registry import Registry
from .utils import EventListener, deprecated, singleton

__all__ = [
    "CategoryRuleRegistry",
    "add_registry_rule_callback",
    "get_category_rules_registry",
    "register_rule",
    "unregister_rule",
]


@singleton
class CategoryRuleRegistry(Registry[str, list[type[BaseRuleChecker]]]):
    """
    A singleton mutable registry of all rules grouped by categories.
    """

    @property
    def categories(self) -> Sequence[str]:
        """
        An immutable list of categories.
        """
        return tuple(category for category in self.keys())

    @property
    def rules(self) -> Sequence[type[BaseRuleChecker]]:
        """
        An immutable list of rules.
        """
        return tuple(rule for rules in self.values() for rule in rules)

    def add(self, category: str, rule: type[BaseRuleChecker]) -> None:
        """
        Associate a rule to a specific category. If the rule was associated to a previous category, it is removed and
        added into the new category.

        Args:
            category (str): The category to associate to the rule.
            rule (Type[BaseRuleChecker]): The rule class.
        """
        self.remove(rule)  # Remove from any existing category
        rules: list[type[BaseRuleChecker]] = self.get(category, [])
        rules.append(rule)
        super().add(category, rules)

    def get_rules(self, category: str) -> list[type[BaseRuleChecker]]:
        """
        Get the rules associated to a specific category in the registry.

        Args:
            category: The category in the registry.

        Returns:
            The rules associated to the category.
        """
        return self.get(category, [])

    def remove(self, rule: type[BaseRuleChecker]) -> None:
        """
        Removes a rule from the registry.

        Args:
            rule: The rule to remove from the registry.
        """
        with self.event_stream:
            for key, rules in list(self.items()):
                if rule in rules:
                    rules.remove(rule)
                    if not rules:
                        del self[key]
                    self.event_stream.notify()

    def find_rule(self, rule_name: str) -> type[BaseRuleChecker] | None:
        """
        Returns:
            Find rule by name. Returns None otherwise.
        """
        for rule in self.rules:
            if rule.__name__ == rule_name:
                return rule
        return None

    def get_category(self, rule: type[BaseRuleChecker]) -> str | None:
        """
        Returns the category under the rule is associated.

        Args:
            rule: The rule in the registry.

        Returns:
            The category under the rule is associated. Returns None if the rule is not registered.
        """
        for key, rules in self.items():
            if rule in rules:
                return key
        return None


def register_rule(
    category: str,
    *,
    skip: bool = False,
    overwrite: type[BaseRuleChecker] | None = None,
) -> Callable[[type[BaseRuleChecker]], type[BaseRuleChecker]]:
    """Decorator. Register a new :py:class:`BaseRuleChecker` to a specific category.

    Example:

    Register MyRule into the category "MyCategory" so that becomes part of the default initialized ValidationEngine.

    .. code-block:: python

        @register_rule("MyCategory")
        class MyRule(BaseRuleChecker):
            pass


    To skip rule registration, use the ``skip`` parameter. This can be useful for testing.

    .. code-block:: python

        @register_rule("MyCategory", skip=True)
        class MyRule(BaseRuleChecker):
            pass

    To overwrite a rule, use the ``overwrite`` parameter. This can be useful to override a rule for a specific category.

    .. code-block:: python

        @register_rule("MyCategory", overwrite=OtherRule)
        class MyRule(BaseRuleChecker):
            pass

    Args:
        category (str): The label with which this rule will be associated
        skip (bool): Optional. Whether to skip rule registration. Default false.
        overwrite (type[BaseRuleChecker] | None): Optional. The rule to overwrite. Default None.
    """

    def _registerRule(rule_class: type[BaseRuleChecker]) -> type[BaseRuleChecker]:
        """
        Take the rule class and register under specific category.
        Return the rule class un altered.
        """
        if skip:
            return rule_class
        registry: CategoryRuleRegistry = CategoryRuleRegistry()
        with registry.event_stream:
            if overwrite is not None:
                registry.remove(overwrite)
            registry.add(category, rule_class)
        return rule_class

    return _registerRule


def unregister_rule(rule: type[BaseRuleChecker]) -> None:
    """
    Unregister a rule from the registry.

    Args:
        rule: The rule to unregister
    """
    CategoryRuleRegistry().remove(rule)


def add_registry_rule_callback(callback: Callable[[], None]) -> EventListener:
    """
    Add a callback to be called when a rule is registered or deregistered.
    It returns a subscription object that can be used to unsubscribe.

    Example:

    .. code-block:: python

        subscription = add_registry_rule_callback(lambda: print("Rule registered"))

        @register_rule("MyCategory")
        class MyRule(BaseRuleChecker):
            pass

        # Output:
        # Rule registered
    """
    return CategoryRuleRegistry().add_callback(callback)


@cache
@deprecated("Use CategoryRuleRegistry instead")
def get_category_rules_registry() -> CategoryRuleRegistry:
    """
    Returns:
        A singleton mutable category rule registry. By default, this includes all rules found in this module
        except for AtomicAsset rules.
    """
    return CategoryRuleRegistry()
