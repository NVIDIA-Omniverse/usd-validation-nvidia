# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from dataclasses import dataclass, field
from typing import Any

from ._requirements import Requirement, RequirementRef


@dataclass(frozen=True)
class Capability:
    """
    Args:
        id: The id of the capability.
        version: The version of the capability.
        path: The path to the capability.
        requirements: The requirements of the capability.
        custom_data: Additional authored fields that are not part of the core capability schema.
    """

    id: str
    version: str
    path: str
    requirements: list[Requirement | RequirementRef] = field(default_factory=list)
    custom_data: dict[str, Any] = field(default_factory=dict)
