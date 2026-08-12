# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from dataclasses import dataclass
from functools import cached_property

from usd_profiles_nvidia.api import Capability, Feature, Requirement

from ._profile import Profile


@dataclass(frozen=True)
class Specifications:
    """
    A collection of specifications.

    Args:
        capabilities: The capabilities of the specifications.
        features: The features of the specifications.
        profiles: The profiles of the specifications.
    """

    capabilities: list[Capability]
    features: list[Feature]
    profiles: list[Profile]

    @cached_property
    def requirements(self) -> list[Requirement]:
        """
        Get the requirements of the specifications.
        """
        return [requirement for capability in self.capabilities for requirement in capability.requirements]
