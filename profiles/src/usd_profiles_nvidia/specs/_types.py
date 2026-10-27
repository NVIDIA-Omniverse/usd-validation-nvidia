# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

from usd_profiles_nvidia.api import (
    Capability,
    Feature,
    Profile,
    Requirement,
    RequirementRef,
)

__all__ = [
    "LoadedSpecificationsProtocol",
    "SpecificationKind",
    "SpecificationProblem",
    "SpecificationProblemKind",
    "SpecificationProblemSeverity",
    "SpecificationRef",
]


@runtime_checkable
class LoadedSpecificationsProtocol(Protocol):
    """Runtime-checkable interface for one loaded specification result."""

    @property
    def capabilities(self) -> Sequence[Capability]: ...

    @property
    def features(self) -> Sequence[Feature]: ...

    @property
    def profiles(self) -> Sequence[Profile]: ...

    @property
    def requirements(self) -> Sequence[Requirement | RequirementRef]: ...

    def validate(self) -> tuple[SpecificationProblem, ...]: ...


class SpecificationKind(str, Enum):
    """Kinds of authored specifications represented in diagnostics."""

    REQUIREMENT = "requirement"
    CAPABILITY = "capability"
    FEATURE = "feature"
    PROFILE = "profile"


class SpecificationProblemKind(str, Enum):
    """Kinds of structural problems in one loaded specification result."""

    MALFORMED_VERSION = "malformed_version"
    DUPLICATE_REQUIREMENT = "duplicate_requirement"
    DUPLICATE_CAPABILITY = "duplicate_capability"
    DUPLICATE_FEATURE = "duplicate_feature"
    DUPLICATE_PROFILE = "duplicate_profile"
    INVALID_PROFILE_FEATURE_OPTIONALITY = "invalid_profile_feature_optionality"


class SpecificationProblemSeverity(str, Enum):
    """Severity of a loaded specification problem."""

    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class SpecificationRef:
    """Stable identifying details for a specification involved in a problem."""

    kind: SpecificationKind
    id: str
    version: str | None = None
    source_label: str | None = None


@dataclass(frozen=True)
class SpecificationProblem:
    """A non-mutating structural diagnostic for loaded specifications."""

    kind: SpecificationProblemKind
    severity: SpecificationProblemSeverity
    source: SpecificationRef
    reference: SpecificationRef | None
    message: str
