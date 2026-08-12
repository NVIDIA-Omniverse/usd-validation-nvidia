# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from typing import Any

from usd_profiles_nvidia.api import Feature, RequirementRef
from usd_profiles_nvidia.model import IdVersion, Version

from ._keystore import PersistentVersionedRegistry


class FeatureStore(PersistentVersionedRegistry[Feature]):
    """
    A store of features.

    Args:
        directory: The directory to load features from.
    """

    def create_key(self, value: Any) -> IdVersion | None:
        if isinstance(value, Feature):
            return IdVersion(value.id, Version(value.version) if value.version else None)
        return None

    def resolve_requirements(self, feature: Feature) -> list[RequirementRef]:
        """
        Return all requirements declared by the feature.

        Args:
            feature: The feature to resolve the requirements for.

        Returns:
            A list of requirements.
        """
        merged: dict[str, RequirementRef] = {}
        for requirement in feature.requirements:
            merged[requirement.code] = requirement
        return list(merged.values())
