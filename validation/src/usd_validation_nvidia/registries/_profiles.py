# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

import logging
from collections.abc import Callable, Iterable

from ..capabilities import (
    CapabilityProtocol,
    FeatureProtocol,
    FeatureRefProtocol,
    ProfileProtocol,
    RequirementRefProtocol,
)
from ..utils import EventListener, SemVer, deprecated, singleton
from ._capabilities import CapabilityRegistry
from ._features import FeatureRegistry
from ._registry import IdVersion, VersionedRegistry
from ._requirements import Requirement, RequirementsRegistry

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

    def get_requirements(
        self, profile: Profile, *, optional: bool = True, recursive: bool = True
    ) -> list[Requirement | RequirementRefProtocol]:
        """
        Return requirements owned by a profile.

        Use profile_features when present, otherwise legacy features and
        capabilities. Resolve feature references through FeatureRegistry, then
        CapabilityRegistry. Include feature dependencies by default.

        Args:
            profile: The profile whose requirements should be returned.
            optional: Include optional profile features when available.
            recursive: Include requirements from feature dependencies.

        Returns:
            Unique requirements per code and version.
        """
        capability_registry = CapabilityRegistry()
        feature_registry = FeatureRegistry()
        requirements_registry = RequirementsRegistry()
        requirements: list[Requirement | RequirementRefProtocol] = []

        if profile_features := getattr(profile, "profile_features", ()):
            for profile_feature in profile_features:
                if profile_feature.optional and not optional:
                    continue
                if isinstance(profile_feature.feature, FeatureProtocol):
                    requirements.extend(feature_registry.get_requirements(profile_feature.feature, recursive=recursive))
                elif isinstance(profile_feature.feature, CapabilityProtocol):
                    requirements.extend(profile_feature.feature.requirements)
                else:
                    feature_id: str = profile_feature.feature.id
                    feature_version: str | None = profile_feature.feature.version
                    feature_requirements: list[Requirement | RequirementRefProtocol] | None = None
                    if isinstance(profile_feature.feature, FeatureRefProtocol):
                        if feature := feature_registry.find(feature_id, feature_version):
                            feature_requirements = feature_registry.get_requirements(feature, recursive=recursive)
                        elif capability := capability_registry.find(feature_id, feature_version):
                            feature_requirements = capability.requirements
                    if feature_requirements is not None:
                        requirements.extend(feature_requirements)
                    elif not profile_feature.optional:
                        raise ValueError(
                            f"Required feature {feature_id!r} version {feature_version!r} "
                            f"referenced by profile {profile.id!r} version {profile.version!r} is not registered"
                        )
        else:
            for feature in getattr(profile, "features", ()):
                requirements.extend(feature_registry.get_requirements(feature, recursive=recursive))

            for capability in getattr(profile, "capabilities", ()):
                requirements.extend(capability.requirements)

        requirements_by_key: dict[tuple[str, str | None], Requirement | RequirementRefProtocol] = {}
        for requirement in requirements_registry.resolve_requirements(requirements):
            requirements_by_key[(requirement.code, requirement.version)] = requirement
        return list(requirements_by_key.values())

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
