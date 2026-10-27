# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from ..capabilities import RequirementRefProtocol
from ._capabilities import Capability, register_capabilities, unregister_capabilities
from ._features import Feature, register_features, unregister_features
from ._profiles import Profile, register_profiles, unregister_profiles
from ._requirements import Requirement, register_requirements, unregister_requirements

__all__ = [
    "register_content",
    "unregister_content",
]


class _LoadedSpecificationsProtocol(Protocol):
    """Specification content produced by usd_profiles_nvidia.SpecificationsLoader."""

    capabilities: Sequence[Capability]
    requirements: Sequence[Requirement | RequirementRefProtocol]
    features: Sequence[Feature]
    profiles: Sequence[Profile]


def register_content(content: _LoadedSpecificationsProtocol) -> None:
    """Register loaded requirement, capability, feature, and profile specification content."""
    requirements = tuple(content.requirements)
    if requirements:
        register_requirements(*requirements)(None)
    register_capabilities(tuple(content.capabilities))
    register_features(tuple(content.features))
    register_profiles(tuple(content.profiles))


def unregister_content(content: _LoadedSpecificationsProtocol) -> None:
    """Unregister loaded specification content in reverse dependency order."""
    unregister_profiles(tuple(content.profiles))
    unregister_features(tuple(content.features))
    unregister_capabilities(tuple(content.capabilities))
    requirements = tuple(content.requirements)
    if requirements:
        unregister_requirements(*requirements)
