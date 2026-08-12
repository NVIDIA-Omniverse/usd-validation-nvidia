# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ._requirements import Requirement, RequirementRef


@dataclass(frozen=True)
class FeatureRef:
    """
    A reference to another feature.

    Args:
        id: A unique identifier of the referenced feature.
        version: The version of the referenced feature.
    """

    id: str
    version: str | None = None


@dataclass(frozen=True)
class Feature:
    """
    Args:
        id: The id of the feature.
        version: The version of the feature.
        path: The path to the feature.
        requirements: The requirements of the feature.
        dependencies: Other features this feature depends on.
        custom_data: Additional authored fields that are not part of the core feature schema.
    """

    id: str
    version: str
    path: str
    requirements: list[Requirement | RequirementRef] = field(default_factory=list)
    dependencies: list[Feature | FeatureRef] = field(default_factory=list)
    custom_data: dict[str, Any] = field(default_factory=dict)
