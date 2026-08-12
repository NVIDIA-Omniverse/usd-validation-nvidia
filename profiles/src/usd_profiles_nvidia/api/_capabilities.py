# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from dataclasses import dataclass, field

from ._requirements import Requirement, RequirementRef


@dataclass(frozen=True)
class Capability:
    """
    Args:
        id: The id of the capability.
        version: The version of the capability.
        path: The path to the capability.
        requirements: The requirements of the capability.
    """

    id: str
    version: str
    path: str
    requirements: list[Requirement | RequirementRef] = field(default_factory=list)
