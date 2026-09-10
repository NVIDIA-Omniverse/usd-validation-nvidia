# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

import importlib
import inspect
import os
import sys
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from functools import singledispatch
from pathlib import Path
from types import ModuleType, TracebackType

from ._base_rule_checker import BaseRuleChecker
from ._categories import CategoryRuleRegistry, unregister_rule
from ._requirements import RequirementsRegistry, unregister_requirements
from .utils import singleton

__all__ = [
    "RegisteredValidationModules",
    "register_validation_modules",
    "unregister_validation_modules",
]


@dataclass(frozen=True)
class RegisteredValidationModules:
    """
    Lifecycle token returned by register_validation_modules.

    Attributes:
        rules: Rule classes loaded or registered by the module registration call.
        modules: Modules loaded by the module registration call.
        module_names: Module names derived from ``modules``.
        paths: Paths added to sys.path by the module registration call.
    """

    rules: tuple[type[BaseRuleChecker], ...]
    modules: tuple[ModuleType, ...] = ()
    paths: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "rules", tuple(dict.fromkeys(self.rules)))
        object.__setattr__(self, "modules", tuple(dict.fromkeys(self.modules)))
        object.__setattr__(self, "paths", tuple(dict.fromkeys(self.paths)))

    @property
    def module_names(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(module.__name__ for module in self.modules))

    def has_rule_name(self, rule_name: str) -> bool:
        return any(rule.__name__ == rule_name for rule in self.rules)

    def has_module_name(self, module_name: str) -> bool:
        return module_name in self.module_names


@singledispatch
def register_validation_modules(module_paths: object) -> RegisteredValidationModules:
    """
    Import loose local validation modules and return the rule classes they register.

    Module paths are re-executed on every call by invalidating import caches and
    removing matching entries from ``sys.modules`` before import. A module name
    may be registered again after its previous token has been unregistered, but
    overlapping active registrations for the same module name are rejected.

    Args:
        module_paths: A single Python file/package directory path, or a list/tuple of paths.

    Returns:
        A lifecycle token containing the loaded module and rule details.
    """
    raise TypeError("register_validation_modules expects a path or a list/tuple of paths.")


@register_validation_modules.register(str)
@register_validation_modules.register(os.PathLike)
def _(module_path: str | os.PathLike[str]) -> RegisteredValidationModules:
    return register_validation_modules([module_path])


@register_validation_modules.register(list)
@register_validation_modules.register(tuple)
def _(
    module_paths: list[str | os.PathLike[str]] | tuple[str | os.PathLike[str], ...],
) -> RegisteredValidationModules:
    with _ValidationModulesLoader() as loader:
        return loader.load(module_paths)


def unregister_validation_modules(registered_modules: RegisteredValidationModules) -> None:
    """
    Unregister rules loaded by :py:func:`register_validation_modules`.

    Args:
        registered_modules: The lifecycle token returned by ``register_validation_modules``.
    """
    _ValidationModulesLoader.unload(registered_modules)


@singleton
@dataclass
class _ValidationModuleRegistry:
    modules: dict[str, ModuleType] = field(default_factory=dict, init=False)

    def validate(self, module_names: Iterable[str]) -> None:
        module_names = tuple(module_names)
        unique_module_names = tuple(dict.fromkeys(module_names))
        most_common_module_name = Counter(module_names).most_common(1)
        if most_common_module_name and most_common_module_name[0][1] > 1:
            raise ValueError(
                "Validation module paths resolve to duplicate module name(s): " + most_common_module_name[0][0]
            )

        registered_module_names = set(self.modules.keys()) | self.rule_module_names
        active_module_names = tuple(
            module_name
            for module_name in unique_module_names
            if module_name in registered_module_names
            or any(
                registered_module_name.startswith(f"{module_name}.")
                for registered_module_name in registered_module_names
            )
        )
        if active_module_names:
            raise ValueError(
                "Validation module(s) already registered: "
                + ", ".join(active_module_names)
                + ". Unregister the previous token before registering them again."
            )

    def register(self, registered_modules: RegisteredValidationModules) -> None:
        self.modules.update({module.__name__: module for module in registered_modules.modules})

    def unregister(self, registered_modules: RegisteredValidationModules) -> None:
        for module in registered_modules.modules:
            if self.modules.get(module.__name__) is module:
                del self.modules[module.__name__]

    @property
    def rule_module_names(self) -> set[str]:
        rules = list(CategoryRuleRegistry().rules) + list(RequirementsRegistry().rules)
        return {rule.__module__ for rule in rules}


class _ValidationModulesLoader:
    def __init__(self) -> None:
        self._category_rules_before: set[type[BaseRuleChecker]] = set()
        self._requirement_rules_before: set[type[BaseRuleChecker]] = set()
        self._owned_search_paths: list[str] = []
        self._attempted_module_names: list[str] = []

    def __enter__(self) -> _ValidationModulesLoader:
        self._category_rules_before = set(CategoryRuleRegistry().rules)
        self._requirement_rules_before = set(RequirementsRegistry().rules)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        _exc_value: BaseException | None,
        _traceback: TracebackType | None,
    ) -> bool:
        if exc_type is not None:
            for rule in self._new_registry_rules():
                unregister_rule(rule)
                unregister_requirements(rule)
            for module_name in self._attempted_module_names:
                self._evict_module(module_name)
            self._release_search_paths(self._owned_search_paths)
        return False

    def load(self, module_paths: Iterable[str | os.PathLike[str]]) -> RegisteredValidationModules:
        import_targets = [self._module_import_parts(Path(path)) for path in module_paths]
        _ValidationModuleRegistry().validate(module_name for _, module_name in import_targets)

        ensured_search_paths: set[str] = set()
        modules: list[ModuleType] = []

        for search_path, module_name in import_targets:
            if search_path not in ensured_search_paths:
                ensured_search_paths.add(search_path)
                owned_search_path = self._ensure_search_path(search_path)
                if owned_search_path is not None:
                    self._owned_search_paths.append(owned_search_path)
            self._evict_module(module_name)
            importlib.invalidate_caches()
            self._attempted_module_names.append(module_name)
            module = importlib.import_module(module_name)
            modules.append(module)

        rules = self._new_registry_rules() + list(self._loaded_module_rules(modules))
        registered_modules = RegisteredValidationModules(
            tuple(rules),
            modules=tuple(modules),
            paths=tuple(self._owned_search_paths),
        )
        _ValidationModuleRegistry().register(registered_modules)
        return registered_modules

    @classmethod
    def unload(cls, registered_modules: RegisteredValidationModules) -> None:
        for rule in reversed(registered_modules.rules):
            unregister_rule(rule)
            unregister_requirements(rule)
        for module in registered_modules.modules:
            cls._evict_module(module.__name__, module)
        _ValidationModuleRegistry().unregister(registered_modules)
        cls._release_search_paths(registered_modules.paths)

    @staticmethod
    def _module_import_parts(module_path: Path) -> tuple[str, str]:
        path = module_path.resolve()
        if path.is_dir():
            if not (path / "__init__.py").is_file():
                raise ValueError(f"Validation module package path {path} must contain __init__.py")
            return str(path.parent), path.name
        if not path.is_file():
            raise FileNotFoundError(path)
        if path.suffix.lower() != ".py":
            raise ValueError(f"Validation module path {path} must be a Python file")
        return str(path.parent), path.stem

    @staticmethod
    def _ensure_search_path(search_path: str) -> str | None:
        if search_path in sys.path:
            return None
        sys.path.insert(0, search_path)
        return search_path

    @staticmethod
    def _release_search_paths(search_paths: Iterable[str]) -> None:
        for search_path in search_paths:
            if search_path in sys.path:
                sys.path.remove(search_path)

    @staticmethod
    def _evict_module(module_name: str, expected_module: ModuleType | None = None) -> None:
        if expected_module is not None and sys.modules.get(module_name) is not expected_module:
            return
        prefix = f"{module_name}."
        for name in [name for name in sys.modules if name == module_name or name.startswith(prefix)]:
            del sys.modules[name]

    def _new_registry_rules(self) -> list[type[BaseRuleChecker]]:
        category_rules = [rule for rule in CategoryRuleRegistry().rules if rule not in self._category_rules_before]
        requirement_rules = [
            rule for rule in RequirementsRegistry().rules if rule not in self._requirement_rules_before
        ]
        return list(dict.fromkeys(category_rules + requirement_rules))

    @staticmethod
    def _loaded_module_rules(modules: Iterable[ModuleType]) -> Iterator[type[BaseRuleChecker]]:
        module_names = tuple(module.__name__ for module in modules)
        prefixes = tuple(f"{module_name}." for module_name in module_names)
        seen_modules: set[str] = set()
        for name, module in list(sys.modules.items()):
            if name not in module_names and not name.startswith(prefixes):
                continue
            if not isinstance(module, ModuleType) or name in seen_modules:
                continue
            seen_modules.add(name)
            for _, candidate in inspect.getmembers(module, inspect.isclass):
                if candidate is BaseRuleChecker:
                    continue
                if candidate.__module__ != module.__name__:
                    continue
                if issubclass(candidate, BaseRuleChecker):
                    yield candidate
