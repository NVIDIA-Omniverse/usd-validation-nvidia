# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

import logging
from collections.abc import Callable, Iterable

from ._registry import IdVersion, VersionedRegistry
from ._requirements import Requirement, RequirementsRegistry
from .capabilities import FeatureProtocol, FeatureRefProtocol, RequirementRefProtocol
from .utils import EventListener, SemVer, singleton

__all__ = [
    "Feature",
    "FeatureRegistry",
    "add_registry_feature_callback",
    "register_feature",
    "register_features",
    "unregister_feature",
    "unregister_features",
]


logger = logging.getLogger(__name__)


Feature = FeatureProtocol
""" Left for backwards compatibility. """


@singleton
class FeatureRegistry(VersionedRegistry[Feature]):
    """
    A registry of features.
    """

    def __init__(self):
        super().__init__()

    def create_key(self, value: Feature) -> IdVersion:
        return IdVersion(value.id, SemVer(value.version))

    @property
    def features(self) -> list[Feature]:
        """Get all features (all versions)."""
        return list(self)

    @property
    def latest_features(self) -> list[Feature]:
        """Get only the latest version of each feature."""
        return self.latest_values()

    def get_requirements(self, feature: Feature | FeatureRefProtocol) -> list[Requirement | RequirementRefProtocol]:
        """
        Return requirements owned by a feature and its resolved feature dependencies.
        """
        registry = RequirementsRegistry()
        requirements: list[Requirement | RequirementRefProtocol] = []
        queue: list[FeatureProtocol | FeatureRefProtocol] = [feature]
        seen: set[tuple[str, str | None]] = set()
        while queue:
            current: FeatureProtocol | FeatureRefProtocol = queue.pop()
            if (current.id, current.version) in seen:
                continue
            if not hasattr(current, "requirements"):
                resolved: Feature = self.find(current.id, current.version)
                if resolved is None:
                    continue
                current = resolved
            key: tuple[str, str | None] = (current.id, current.version)
            if key in seen:
                continue
            seen.add(key)
            requirements.extend(registry.resolve_requirements(current.requirements))
            dependencies = getattr(current, "dependencies", [])
            if isinstance(dependencies, Iterable):
                queue.extend(dependencies)
        return requirements

    def remove(self, feature: Feature) -> None:
        """
        Remove a feature from the registry.

        Args:
            feature: The feature to remove

        Raises:
            ValueError: If the feature has requirements that are implemented
        """
        registry = RequirementsRegistry()
        if registry.get_validators(feature.requirements):
            raise ValueError(f"Feature {feature} has requirements that are implemented")
        super().remove(feature)


def register_feature(feature: Feature) -> None:
    """
    Register a feature.

    Args:
        feature: The feature to register.
    """
    FeatureRegistry().add(feature)


def unregister_feature(feature: Feature) -> None:
    """
    Unregister a feature.

    Args:
        feature: The feature to unregister.
    """
    FeatureRegistry().remove(feature)


def register_features(features: Iterable[Feature]) -> bool:
    """
    Register multiple features, skipping any already registered.

    Args:
        features: An iterable of features to register.

    Returns:
        True if every feature was registered, False if any were skipped.
    """
    flag: bool = True
    for feature in features:
        try:
            register_feature(feature)
        except ValueError:
            logger.debug(f"Feature {feature} already registered, skipping")
            flag = False
    return flag


def unregister_features(features: Iterable[Feature]) -> bool:
    """
    Unregister multiple features, skipping any still in use.

    Args:
        features: An iterable of features to unregister.

    Returns:
        True if every feature was unregistered, False if any were skipped.
    """
    flag: bool = True
    for feature in features:
        try:
            unregister_feature(feature)
        except ValueError:
            logger.debug(f"Feature {feature} still in use, skipping")
            flag = False
    return flag


def add_registry_feature_callback(callback: Callable[[], None]) -> EventListener:
    """
    Add a callback to be called when a feature is registered or deregistered.
    Returns a subscription object that can be used to unsubscribe.

    Args:
        callback: The callback to add.

    Returns:
        A subscription object that can be used to unsubscribe.
    """
    return FeatureRegistry().add_callback(callback)
