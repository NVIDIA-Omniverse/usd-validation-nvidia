# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import logging
from collections.abc import Callable, Iterable
from typing import Protocol, runtime_checkable

from ._deprecate import deprecated
from ._events import EventListener
from ._registry import IdVersion, VersionedRegistry
from ._requirements import Requirement, RequirementsRegistry
from ._semver import SemVer
from ._singleton import singleton

__all__ = [
    "Capability",
    "CapabilityRegistry",
    "add_registry_capability_callback",
    "register_capabilities",
    "register_capability",
    "unregister_capabilities",
    "unregister_capability",
]


@runtime_checkable
class Capability(Protocol):
    """
    A protocol definition of capability.

    Attributes:
        id: A unique identifier of the capability
        version: The version of the capability
        path: The path to the capability
        requirements: The requirements of the capability
    """

    id: str
    version: str
    path: str
    requirements: list[Requirement]


@singleton
class CapabilityRegistry(VersionedRegistry[Capability]):
    """
    A singleton class that keeps capabilities.
    """

    def __init__(self):
        super().__init__()

    def create_key(self, value: Capability) -> IdVersion:
        return IdVersion(value.id, SemVer(value.version))

    @property
    def capabilities(self) -> list[Capability]:
        """Get all capabilities (all versions)."""
        return list(self)

    @property
    def latest_capabilities(self) -> list[Capability]:
        """Get only the latest version of each capability."""
        return self.latest_values()

    def remove(self, capability: Capability) -> None:
        """
        Remove a capability from the registry.

        Args:
            capability: The capability to remove

        Raises:
            ValueError: If the capability has requirements that are implemented
        """
        registry = RequirementsRegistry()
        if registry.get_validators(capability.requirements):
            raise ValueError(f"Capability {capability} has requirements that are implemented")
        super().remove(capability)

    @deprecated("Use keys() instead")
    def get_capability_ids(self) -> list[str]:
        return [key.id for key in self.keys()]

    @deprecated("Use add() instead")
    def add_capability(self, capability: Capability) -> None:
        """
        Add a capability to the registry.

        Args:
            capability: The capability to add

        Raises:
            ValueError: If a capability with the same ID and version already exists
        """
        self.add(capability)

    @deprecated("Use find() instead")
    def find_capability(self, id: str, version: str | None = None) -> Capability | None:
        """
        Find a capability by ID and version.

        Args:
            id: The capability ID
            version: The version to find, defaults to latest

        Returns:
            The capability if found, None otherwise
        """
        return self.find(id, version)


def register_capability(capability: Capability) -> None:
    """
    Register a capability.

    Args:
        capability: The capability to register.
    """
    CapabilityRegistry().add(capability)


def unregister_capability(capability: Capability) -> None:
    """
    Unregister a capability.

    Args:
        capability: The capability to unregister.
    """
    CapabilityRegistry().remove(capability)


def register_capabilities(capabilities: Iterable[Capability]) -> None:
    """
    Register multiple capabilities, skipping any already registered.

    Args:
        capabilities: An iterable of capabilities to register.
    """
    for capability in capabilities:
        try:
            register_capability(capability)
        except ValueError:
            logging.info(f"Capability {capability} already registered, skipping")


def unregister_capabilities(capabilities: Iterable[Capability]) -> None:
    """
    Unregister multiple capabilities, skipping any still in use.

    Args:
        capabilities: An iterable of capabilities to unregister.
    """
    for capability in capabilities:
        try:
            unregister_capability(capability)
        except ValueError:
            logging.info(f"Capability {capability} still in use, skipping")


def add_registry_capability_callback(callback: Callable[[], None]) -> EventListener:
    """
    Add a callback to be called when a capability is registered or deregistered.
    Returns a subscription object that can be used to unsubscribe.

    Args:
        callback: The callback to add.

    Returns:
        A subscription object that can be used to unsubscribe.
    """
    return CapabilityRegistry().add_callback(callback)
