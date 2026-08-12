# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from dataclasses import dataclass, field

from usd_profiles_nvidia.api import FeatureRef, RequirementRef

from ._model import Model


@dataclass(slots=True)
class Feature(Model):
    """
    Represents a feature of a capability.

    Args:
        requirements (list[RequirementRef]): The requirements of the feature.
        dependencies (list[FeatureRef]): Other features this feature depends on.
    """

    requirements: list[RequirementRef] = field(default_factory=list)
    dependencies: list[FeatureRef] = field(default_factory=list)
