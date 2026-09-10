# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Iterator

from ._features import FeatureRegistry
from ._registry import IdVersion, VersionedRegistry
from ._requirements import Requirement, RequirementsRegistry
from .capabilities import (
    FeatureProtocol,
    ProfileProtocol,
    RequirementRefProtocol,
)
from .utils import EventListener, SemVer, deprecated, singleton

__all__ = [
    "Profile",
    "ProfileRegistry",
    "add_registry_profile_callback",
    "register_profile",
    "register_profiles",
    "unregister_profile",
    "unregister_profiles",
]


logger = logging.getLogger(__name__)


Profile = ProfileProtocol
""" Left for backwards compatibility. """


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

    def get_requirements(self, profile: Profile) -> list[Requirement | RequirementRefProtocol]:
        """
        Return requirements owned by a profile's features, feature dependencies, and capabilities.
        """
        feature_registry = FeatureRegistry()
        registry = RequirementsRegistry()
        requirements: list[Requirement | RequirementRefProtocol] = []
        for feature in self._resolved_features(profile, feature_registry):
            requirements.extend(feature_registry.get_requirements(feature))
        for capability in getattr(profile, "capabilities", ()):
            requirements.extend(registry.resolve_requirements(capability.requirements))
        return requirements

    @classmethod
    def _resolved_features(
        cls,
        profile: Profile,
        registry: FeatureRegistry,
        *,
        allow_unresolved_required: bool = False,
    ) -> Iterator[FeatureProtocol]:
        """Yield concrete profile features and compatible registered values for references."""
        feature_entries = (
            ((profile_feature.feature, profile_feature.optional) for profile_feature in profile.profile_features)
            if profile.profile_features
            else ((feature, False) for feature in profile.features)
        )
        for feature, optional in feature_entries:
            if not hasattr(feature, "requirements"):
                reference = feature
                feature = registry.resolve(reference.id, reference.version)
                if feature is None and not (optional or allow_unresolved_required):
                    raise ValueError(
                        f"Required feature {reference.id!r} version {reference.version!r} "
                        f"referenced by profile {profile.id!r} version {profile.version!r} is not registered"
                    )
            if feature is None:
                continue
            yield feature

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


def register_profiles(profiles: Iterable[Profile]) -> bool:
    """
    Register multiple profiles, skipping any already registered.

    Args:
        profiles: An iterable of profiles to register.

    Returns:
        True if every profile was registered, False if any were skipped.
    """
    flag: bool = True
    for profile in profiles:
        try:
            register_profile(profile)
        except ValueError:
            logger.debug(f"Profile {profile} already registered, skipping")
            flag = False
    return flag


def unregister_profiles(profiles: Iterable[Profile]) -> bool:
    """
    Unregister multiple profiles by ID and version, skipping any not registered.

    Args:
        profiles: An iterable of profiles to unregister.

    Returns:
        True if every profile was unregistered, False if any were missing.
    """
    flag: bool = True
    for profile in profiles:
        try:
            unregister_profile(profile)
        except ValueError:
            logger.debug(f"Profile {profile} not registered, skipping")
            flag = False
    return flag


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
