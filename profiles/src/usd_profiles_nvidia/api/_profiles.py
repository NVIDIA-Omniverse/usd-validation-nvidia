# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from dataclasses import dataclass, field

from ._capabilities import Capability
from ._features import Feature, FeatureRef


@dataclass(frozen=True)
class ProfileFeature:
    """
    Args:
        feature: The feature of the profile.
        optional: Whether the feature is optional in the profile.
    """

    feature: Feature | FeatureRef
    optional: bool = False


@dataclass(frozen=True)
class Profile:
    """
    Args:
        id: The id of the profile.
        version: The version of the profile.
        path: The path to the profile.
        features: The features of the profile.
        capabilities: The capabilities of the profile.
        profile_features: The profile feature references.
        display_name: A human-readable profile name.
        message: A description of the profile.
    """

    id: str
    version: str | None
    path: str
    features: list[Feature | FeatureRef] = field(default_factory=list)
    capabilities: list[Capability] = field(default_factory=list)
    profile_features: list[ProfileFeature] = field(default_factory=list)
    display_name: str | None = None
    message: str | None = None
