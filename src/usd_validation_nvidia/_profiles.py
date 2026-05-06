# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from typing import Protocol, runtime_checkable

from ._capabilities import Capability
from ._deprecate import deprecated
from ._events import EventListener
from ._registry import IdVersion, VersionedRegistry
from ._requirements import Requirement, RequirementsRegistry
from ._semver import SemVer
from ._singleton import singleton

__all__ = [
    "Profile",
    "ProfileRegistry",
    "add_registry_profile_callback",
    "register_profile",
    "register_profiles",
    "unregister_profile",
    "unregister_profiles",
]


@runtime_checkable
class Profile(Protocol):
    """
    A protocol definition of profile.

    Attributes:
        id: A unique identifier of the profile
        version: The version of the profile
        path: The path to the profile
        capabilities: The capabilities of the profile
    """

    id: str
    version: str
    path: str
    capabilities: list[Capability]


@singleton
class ProfileRegistry(VersionedRegistry[Profile]):
    """
    A singleton class that keeps profiles.
    """

    def __init__(self):
        super().__init__()

    def create_key(self, value: Profile) -> IdVersion:
        return IdVersion(value.id, SemVer(value.version))

    @property
    def profiles(self) -> list[Profile]:
        """Get all profiles (all versions)."""
        return list(self)

    def remove(self, profile: Profile) -> None:
        """
        Remove a profile from the registry.

        Args:
            profile: The profile to remove

        Raises:
            ValueError: If the profile has requirements that are implemented
        """
        registry = RequirementsRegistry()
        requirements: list[Requirement] = [
            requirement for capability in profile.capabilities for requirement in capability.requirements
        ]
        if registry.get_validators(requirements):
            raise ValueError(f"Profile {profile} has requirements that are implemented")
        super().remove(profile)

    @deprecated("Use add() instead")
    def add_profile(self, profile: Profile) -> None:
        """
        Add a profile to the registry.

        Args:
            profile: The profile to add

        Raises:
            ValueError: If a profile with the same ID and version already exists
        """
        self.add(profile)

    @deprecated("Use find() instead")
    def find_profile(self, id: str, version: str | None = None) -> Profile | None:
        """
        Find a profile by ID and version.

        Args:
            id: The profile ID
            version: The version to find, defaults to latest

        Returns:
            The profile if found, None otherwise
        """
        return self.find(id, version)


def register_profile(profile: Profile) -> None:
    """
    Register a profile.

    Args:
        profile: The profile to register.
    """
    ProfileRegistry().add(profile)


def unregister_profile(profile: Profile) -> None:
    """
    Unregister a profile.

    Args:
        profile: The profile to unregister.
    """
    ProfileRegistry().remove(profile)


def register_profiles(profiles: Iterable[Profile]) -> None:
    """
    Register multiple profiles, skipping any already registered.

    Args:
        profiles: An iterable of profiles to register.
    """
    for profile in profiles:
        try:
            register_profile(profile)
        except ValueError:
            logging.info(f"Profile {profile} already registered, skipping")


def unregister_profiles(profiles: Iterable[Profile]) -> None:
    """
    Unregister multiple profiles, skipping any still in use.

    Args:
        profiles: An iterable of profiles to unregister.
    """
    for profile in profiles:
        try:
            unregister_profile(profile)
        except ValueError:
            logging.info(f"Profile {profile} still in use, skipping")


def add_registry_profile_callback(callback: Callable[[], None]) -> EventListener:
    """
    Add a callback to be called when a profile is registered or deregistered.
    Returns a subscription object that can be used to unsubscribe.

    Args:
        callback: The callback to add.

    Returns:
        A subscription object that can be used to unsubscribe.
    """
    return ProfileRegistry().add_callback(callback)
