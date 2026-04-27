# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
"""
Plugin management system for the Omniverse Asset Validator.

This module provides a standardized entrypoint-based plugin registration mechanism,
enabling external packages to register validation rules, requirements, features, and
profiles through Python entrypoints.

The built-in validation rules are registered via ``DefaultPlugin``, which is loaded
by default. External plugins are discovered via the ``nvidia_usd_validation`` entrypoint
group and are expected to provide an object with ``on_startup()`` and ``on_shutdown()`` methods.

Example plugin entrypoint in ``pyproject.toml``::

    [project.entry-points."nvidia_usd_validation"]
    registrant = "my_package.validator_plugin:plugin_instance"

Example plugin implementation::

    class MyValidatorPlugin:
        def on_startup(self) -> None:
            # Register rules, requirements, etc.
            pass

        def on_shutdown(self) -> None:
            # Clean up resources if needed
            pass

    plugin_instance = MyValidatorPlugin()
"""
from __future__ import annotations

import importlib.metadata
import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache
from graphlib import CycleError, TopologicalSorter
from typing import Protocol, runtime_checkable

from ._singleton import singleton

DEFAULT_PLUGIN_ENTRYPOINT = "nvidia_usd_validation:DefaultPlugin"

__all__ = [
    "LoadedPlugin",
    "PluginManager",
    "PluginProtocol",
]

logger = logging.getLogger(__name__)


@runtime_checkable
class PluginProtocol(Protocol):
    """
    Protocol defining the required interface for Asset Validator plugins.

    All plugins must implement both on_startup() and on_shutdown() methods.
    """

    def on_startup(self) -> None:
        """
        Called when the plugin is started. Plugins should register their
        validation rules, requirements, features, and profiles in this method.
        """
        ...

    def on_shutdown(self) -> None:
        """
        Called when the plugin system is shutting down. Plugins should clean up
        any resources they hold.
        """
        ...


@dataclass
class LoadedPlugin:
    """
    Represents a loaded plugin with its metadata.

    Attributes:
        instance: The plugin instance (must conform to PluginProtocol)
        name: The entrypoint name for this plugin
        distribution_name: The distribution name of the package providing this plugin
        entrypoint: The original entrypoint object
    """

    instance: PluginProtocol
    name: str
    distribution_name: str
    entrypoint: importlib.metadata.EntryPoint

    @property
    def version(self) -> str:
        """Return the installed version of the plugin's distribution package."""
        try:
            return importlib.metadata.version(self.distribution_name)
        except importlib.metadata.PackageNotFoundError:
            return "unknown"


@singleton
class PluginManager:
    """
    Manages the lifecycle of Asset Validator plugins.

    The PluginManager discovers plugins via Python entrypoints, loads them in
    topologically sorted order based on package dependencies, and manages their
    startup and shutdown lifecycle.

    Plugins are discovered from the 'nvidia_usd_validation' entrypoint group.
    This is a singleton class - calling PluginManager() always returns the same instance.

    Use as a context manager for automatic startup and shutdown::

        with PluginManager():
            # plugins are active
            ...
        # plugins are shut down
    """

    ENTRYPOINT_GROUP = "nvidia_usd_validation"

    def __init__(self):
        """Initialize the plugin manager."""
        self._loaded_plugins: list[LoadedPlugin] = []

    @cache
    def initialize(self) -> None:
        """
        Initialize the plugin system.

        Discovers, loads, and starts all plugins in topologically sorted order.
        This method is idempotent - calling it multiple times has no additional effect.
        """
        logger.info("Initializing Asset Validator plugin system")

        entrypoints = self._discover_entrypoints()
        if not entrypoints:
            logger.info("No plugins discovered")
            return

        for ep in entrypoints:
            if plugin := self._load_and_start_plugin(ep):
                self._loaded_plugins.append(plugin)

        loaded_names = {p.entrypoint.value for p in self._loaded_plugins}
        logger.info(f"Plugin system initialized. Loaded plugins: {loaded_names}")

    def _discover_entrypoints(self) -> list[importlib.metadata.EntryPoint]:
        """
        Discover all entrypoints in the 'nvidia_usd_validation' group.

        Returns all discovered entrypoints in topologically sorted order. If
        the default plugin is not discovered (e.g. dev mode without pip
        install), a synthetic entrypoint is created as fallback.

        Returns:
            List of EntryPoint objects in topologically sorted order.
        """
        try:
            eps = importlib.metadata.entry_points()
            discovered = list(eps.select(group=self.ENTRYPOINT_GROUP))

            discovered_values = {ep.value for ep in discovered}
            logger.info(f"Discovered plugins: {discovered_values}")

            # Fallback: if the default plugin wasn't discovered (e.g. dev/build
            # mode without pip install), create a synthetic entrypoint so it
            # still loads.
            if DEFAULT_PLUGIN_ENTRYPOINT not in discovered_values:
                default_ep = importlib.metadata.EntryPoint(
                    name="default",
                    value=DEFAULT_PLUGIN_ENTRYPOINT,
                    group=self.ENTRYPOINT_GROUP,
                )
                discovered.append(default_ep)

            return self._topological_sort(discovered)

        except (ImportError, AttributeError, ValueError):
            logger.exception("Error discovering entrypoints")
            return []

    def _get_package_dependencies(self, distribution_name: str) -> set[str]:
        """
        Get the set of direct package dependencies for a given distribution.

        Returns:
            Set of distribution names that this distribution depends on
        """
        try:
            deps = importlib.metadata.requires(distribution_name)
            if deps is None:
                return set()

            # Pattern matches valid PEP 508 package identifiers: start with alphanumeric,
            # followed by alphanumerics/hyphens/underscores/dots, end with alphanumeric
            identifier_pattern = re.compile(r"^(?P<identifier>[0-9A-Za-z]([-_.0-9A-Za-z]*[0-9A-Za-z])?).*")
            dependencies = set()
            for dep in deps:
                if match := identifier_pattern.match(dep):
                    dist_name = match.group("identifier")
                    dependencies.add(dist_name)

            return dependencies

        except importlib.metadata.PackageNotFoundError:
            logger.warning(f"Could not find package metadata for '{distribution_name}'")
            return set()
        except (AttributeError, ValueError, TypeError) as e:
            logger.warning(f"Could not determine dependencies for {distribution_name}: {e}")
            return set()

    def _topological_sort(
        self, entrypoints: list[importlib.metadata.EntryPoint]
    ) -> list[importlib.metadata.EntryPoint]:
        """
        Sort entrypoints in topological order based on package dependencies.

        Uses Python's graphlib.TopologicalSorter to ensure packages are loaded after
        their dependencies. If circular dependencies are detected, logs an error and
        returns packages in alphabetical order.

        Returns:
            List of EntryPoint objects in topologically sorted order
        """
        if not entrypoints:
            return []

        # Entrypoints without dist metadata (e.g. dev mode fallback) are
        # placed first since they have no dependency information to sort.
        no_dist = [ep for ep in entrypoints if not ep.dist]
        ep_by_dist = {ep.dist.name: ep for ep in entrypoints if ep.dist}

        graph: dict[str, set[str]] = {}
        for dist_name in ep_by_dist:
            deps = self._get_package_dependencies(dist_name)
            graph[dist_name] = deps & ep_by_dist.keys()

        try:
            sorter = TopologicalSorter(graph)
            sorted_names = list(sorter.static_order())
        except CycleError as e:
            logger.error(f"Circular dependency detected in plugins: {e}. Loading in alphabetical order.")
            sorted_names = sorted(ep_by_dist.keys())

        return no_dist + [ep_by_dist[name] for name in sorted_names]

    def _load_and_start_plugin(self, entrypoint: importlib.metadata.EntryPoint) -> LoadedPlugin | None:
        """
        Load a plugin from an entrypoint and call its on_startup().

        Returns:
            LoadedPlugin instance if successful, None if loading or startup failed
        """
        dist_name = entrypoint.dist.name if entrypoint.dist else entrypoint.value

        try:
            logger.info(f"Loading {self.ENTRYPOINT_GROUP} entrypoint: '{entrypoint.value}'")
            plugin_instance = entrypoint.load()
        except Exception:
            logger.exception(f"Failed to load plugin '{entrypoint.name}' from '{dist_name}'")
            return None

        if isinstance(plugin_instance, type):
            plugin_instance = plugin_instance()
        if not isinstance(plugin_instance, PluginProtocol):
            logger.error(
                f"Plugin '{entrypoint.name}' from '{dist_name}' missing required "
                f"on_startup()/on_shutdown() methods. Skipping."
            )
            return None
        plugin = LoadedPlugin(
            instance=plugin_instance,
            name=entrypoint.name,
            distribution_name=dist_name,
            entrypoint=entrypoint,
        )

        try:
            logger.info(f"Calling '{entrypoint.value}.on_startup()'")
            plugin.instance.on_startup()
            return plugin
        except Exception:
            logger.exception(f"Failed to start plugin '{entrypoint.name}' from '{dist_name}'")
            return None

    def shutdown(self) -> None:
        """
        Shut down all loaded plugins.

        Calls on_shutdown() for all plugins in reverse order of loading.
        Errors during shutdown are logged but do not prevent other plugins from shutting down.
        """
        PluginManager.initialize.cache_clear()

        if not self._loaded_plugins:
            return

        logger.info("Shutting down Asset Validator plugin system")

        for plugin in reversed(self._loaded_plugins):
            try:
                logger.info(f"Calling '{plugin.entrypoint.value}.on_shutdown()'")
                plugin.instance.on_shutdown()
            except Exception:
                logger.exception(f"Error shutting down plugin '{plugin.name}' from '{plugin.distribution_name}'")

        logger.info("Plugin system shutdown complete")
        self._loaded_plugins.clear()

    @property
    def loaded_plugins(self) -> Sequence[LoadedPlugin]:
        """
        Get the list of currently loaded plugins.

        Returns:
            Immutable sequence of LoadedPlugin objects
        """
        return tuple(self._loaded_plugins)

    def get_loaded_plugin(self, entrypoint_value: str) -> LoadedPlugin | None:
        """
        Return the loaded plugin for the given entrypoint value, or ``None`` if not loaded.

        Args:
            entrypoint_value: The entrypoint value string (e.g. ``"nvidia_usd_validation:DefaultPlugin"``).

        Returns:
            The :class:`LoadedPlugin` instance, or ``None`` if not found.
        """
        return next((p for p in self._loaded_plugins if p.entrypoint.value == entrypoint_value), None)

    def is_plugin_loaded(self, entrypoint_value: str) -> bool:
        """
        Check if a plugin is currently loaded.

        Args:
            entrypoint_value: The entrypoint value string (e.g. ``"nvidia_usd_validation:DefaultPlugin"``).

        Returns:
            ``True`` if the plugin is loaded, ``False`` otherwise.
        """
        return self.get_loaded_plugin(entrypoint_value) is not None

    def __enter__(self) -> PluginManager:
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.shutdown()
