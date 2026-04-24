# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from typing import Protocol, runtime_checkable

from ._events import EventListener
from ._registry import IdVersion, VersionedRegistry
from ._requirements import Requirement, RequirementsRegistry
from ._semver import SemVer
from ._singleton import singleton

__all__ = [
    "Feature",
    "FeatureRegistry",
    "add_registry_feature_callback",
    "register_feature",
    "register_features",
    "unregister_feature",
    "unregister_features",
]


@runtime_checkable
class Feature(Protocol):
    """
    A protocol definition of feature.

    Attributes:
        id: A unique identifier of the feature
        version: The version of the feature
        path: The path to the feature
        requirements: The requirements of the feature
    """

    id: str
    version: str
    path: str
    requirements: list[Requirement]


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


def register_features(features: Iterable[Feature]) -> None:
    """
    Register multiple features, skipping any already registered.

    Args:
        features: An iterable of features to register.
    """
    for feature in features:
        try:
            register_feature(feature)
        except ValueError:
            logging.info(f"Feature {feature} already registered, skipping")


def unregister_features(features: Iterable[Feature]) -> None:
    """
    Unregister multiple features, skipping any still in use.

    Args:
        features: An iterable of features to unregister.
    """
    for feature in features:
        try:
            unregister_feature(feature)
        except ValueError:
            logging.info(f"Feature {feature} still in use, skipping")


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
