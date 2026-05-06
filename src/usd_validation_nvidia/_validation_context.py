# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum

from ._capabilities import Capability
from ._features import Feature
from ._profiles import Profile
from ._requirements import Requirement

__all__ = [
    "FeatureStatus",
    "ProfileStatus",
    "RequirementStatus",
    "ValidationContext",
    "ValidationStatus",
]


class ValidationStatus(str, Enum):
    """Pass/fail status for a validation check."""

    PASS = "PASS"
    FAIL = "FAIL"


@dataclass(frozen=True)
class RequirementStatus:
    """Pass/fail status for a single requirement."""

    requirement: Requirement
    status: ValidationStatus


@dataclass(frozen=True)
class FeatureStatus:
    """Pass/fail status for a feature or capability, with per-requirement breakdown."""

    feature: Feature | Capability
    status: ValidationStatus
    requirements: list[RequirementStatus]

    @property
    def failed_requirements(self) -> list[Requirement]:
        """All requirements that failed for this feature, deduplicated."""
        seen: dict[tuple[str, str | None], Requirement] = {}
        for req_status in self.requirements:
            if req_status.status == ValidationStatus.FAIL:
                req = req_status.requirement
                seen[(req.code, req.version)] = req
        return list(seen.values())


@dataclass(frozen=True)
class ProfileStatus:
    """Pass/fail status for a profile, with per-feature breakdown."""

    profile: Profile
    status: ValidationStatus
    features: list[FeatureStatus]

    @property
    def failed_requirements(self) -> list[Requirement]:
        """All requirements that failed across all features of this profile, deduplicated."""
        seen: dict[tuple[str, str | None], Requirement] = {}
        for feature_status in self.features:
            for req in feature_status.failed_requirements:
                seen[(req.code, req.version)] = req
        return list(seen.values())


@dataclass(frozen=True)
class ValidationContext:
    """Structured pass/fail summary produced after profile- or feature-scoped validation.

    ``profiles`` is populated when ``--profile`` is used.
    ``features`` is populated when ``--feature`` or ``--capability`` is used (without a profile).
    """

    profiles: list[ProfileStatus] = field(default_factory=list)
    features: list[FeatureStatus] = field(default_factory=list)

    @property
    def matched_profiles(self) -> list[ProfileStatus]:
        """Profiles that passed all requirements."""
        return [p for p in self.profiles if p.status == ValidationStatus.PASS]

    @property
    def failed_profiles(self) -> list[ProfileStatus]:
        """Profiles that failed one or more requirements."""
        return [p for p in self.profiles if p.status == ValidationStatus.FAIL]

    @property
    def failed_requirements(self) -> list[Requirement]:
        """All requirements that failed across all profiles and features, deduplicated."""
        seen: dict[tuple[str, str | None], Requirement] = {}
        for profile_status in self.profiles:
            for req in profile_status.failed_requirements:
                seen[(req.code, req.version)] = req
        for feature_status in self.features:
            for req in feature_status.failed_requirements:
                seen[(req.code, req.version)] = req
        return list(seen.values())

    @classmethod
    def build(
        cls,
        enabled_profiles: list[Profile],
        enabled_features: list[Feature],
        enabled_capabilities: list[Capability],
        failed_requirements: Iterable[Requirement],
    ) -> ValidationContext | None:
        """Build a typed validation context from engine state and failed requirements.

        Returns ``None`` when no profile/feature/capability scope is active, preserving
        backwards-compatible output for plain rule-based validation.
        """
        if not (enabled_profiles or enabled_features or enabled_capabilities):
            return None

        failed_keys: set[tuple[str, str | None]] = {(r.code, r.version) for r in failed_requirements}

        def _req_status(req: Requirement) -> RequirementStatus:
            status = ValidationStatus.FAIL if (req.code, req.version) in failed_keys else ValidationStatus.PASS
            return RequirementStatus(requirement=req, status=status)

        def _feature_status(feature_like: Feature | Capability) -> FeatureStatus:
            reqs = [_req_status(r) for r in feature_like.requirements]
            status = (
                ValidationStatus.FAIL if any(r.status == ValidationStatus.FAIL for r in reqs) else ValidationStatus.PASS
            )
            return FeatureStatus(feature=feature_like, status=status, requirements=reqs)

        profiles: list[ProfileStatus] = []
        for profile in enabled_profiles:
            # Always resolve through capabilities — mirrors _direct_requirements in the engine,
            # which exclusively uses profile.capabilities when enabling rules.
            features = [_feature_status(cap) for cap in profile.capabilities]
            p_status = (
                ValidationStatus.FAIL
                if any(f.status == ValidationStatus.FAIL for f in features)
                else ValidationStatus.PASS
            )
            profiles.append(ProfileStatus(profile=profile, status=p_status, features=features))

        features: list[FeatureStatus] = []
        if enabled_features:
            features = [_feature_status(f) for f in enabled_features]
        elif enabled_capabilities and not enabled_profiles:
            features = [_feature_status(c) for c in enabled_capabilities]

        return cls(profiles=profiles, features=features)
