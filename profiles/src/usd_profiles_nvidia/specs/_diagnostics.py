# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import singledispatchmethod

from usd_profiles_nvidia.api import (
    Capability,
    Feature,
    FeatureRef,
    Profile,
    Requirement,
    RequirementRef,
)
from usd_profiles_nvidia.model._version import Version

from ._types import (
    LoadedSpecificationsProtocol,
    SpecificationKind,
    SpecificationProblem,
    SpecificationProblemKind,
    SpecificationProblemSeverity,
    SpecificationRef,
)


@dataclass
class _LoadedSpecificationsValidator:
    """Validate one loaded specification result without mutating it."""

    _content: LoadedSpecificationsProtocol
    _problems: list[SpecificationProblem] = field(default_factory=list, init=False)

    def validate(self) -> tuple[SpecificationProblem, ...]:
        """Return local structural problems without resolving references."""
        requirements = tuple(
            requirement for requirement in self._content.requirements if isinstance(requirement, Requirement)
        )
        self._find_duplicates(
            requirements,
            SpecificationKind.REQUIREMENT,
            SpecificationProblemKind.DUPLICATE_REQUIREMENT,
        )
        self._find_duplicates(
            self._content.capabilities,
            SpecificationKind.CAPABILITY,
            SpecificationProblemKind.DUPLICATE_CAPABILITY,
        )
        self._find_duplicates(
            self._content.features,
            SpecificationKind.FEATURE,
            SpecificationProblemKind.DUPLICATE_FEATURE,
        )
        self._find_duplicates(
            self._content.profiles,
            SpecificationKind.PROFILE,
            SpecificationProblemKind.DUPLICATE_PROFILE,
        )

        for capability in self._content.capabilities:
            source = self._object_ref(capability)
            self._check_version(source, capability.version, required=True)
            for requirement in capability.requirements:
                self._check_version(
                    source,
                    requirement.version,
                    reference=self._object_ref(requirement),
                )

        for feature in self._content.features:
            source = self._object_ref(feature)
            self._check_version(source, feature.version, required=True)
            for requirement in feature.requirements:
                self._check_version(
                    source,
                    requirement.version,
                    reference=self._object_ref(requirement),
                )
            for dependency in feature.dependencies:
                self._check_version(
                    source,
                    dependency.version,
                    reference=self._object_ref(dependency),
                )

        for profile in self._content.profiles:
            source = self._object_ref(profile)
            self._check_version(source, profile.version, required=True)
            feature_entries = (
                tuple((entry.feature, entry.optional) for entry in profile.profile_features)
                if profile.profile_features
                else tuple((feature, False) for feature in profile.features)
            )
            for feature, optional in feature_entries:
                reference = self._object_ref(feature)
                self._check_version(source, feature.version, reference=reference)
                if type(optional) is not bool:
                    self._problems.append(
                        SpecificationProblem(
                            kind=SpecificationProblemKind.INVALID_PROFILE_FEATURE_OPTIONALITY,
                            severity=SpecificationProblemSeverity.ERROR,
                            source=source,
                            reference=reference,
                            message=(
                                f"Profile {profile.id!r} version {profile.version!r} marks feature "
                                f"{feature.id!r} with non-boolean optionality {optional!r}"
                            ),
                        )
                    )

        return tuple(dict.fromkeys(self._problems))

    def _find_duplicates(
        self,
        values: Iterable[Requirement | Capability | Feature | Profile],
        object_kind: SpecificationKind,
        problem_kind: SpecificationProblemKind,
    ) -> None:
        seen: set[tuple[str, Version | str | None]] = set()
        for value in values:
            object_ref = self._object_ref(value)
            version_identity: Version | str | None = object_ref.version
            try:
                if object_ref.version is not None:
                    version_identity = Version(object_ref.version)
            except (TypeError, ValueError):
                version_identity = object_ref.version
            key = (object_ref.id, version_identity)
            if key in seen:
                self._problems.append(
                    SpecificationProblem(
                        kind=problem_kind,
                        severity=SpecificationProblemSeverity.ERROR,
                        source=object_ref,
                        reference=None,
                        message=(
                            f"Duplicate {object_kind.value} {object_ref.id!r} version {object_ref.version!r} "
                            "in loaded specifications"
                        ),
                    )
                )
            else:
                seen.add(key)

    def _check_version(
        self,
        source: SpecificationRef,
        version: object,
        *,
        required: bool = False,
        reference: SpecificationRef | None = None,
    ) -> None:
        if version is None and not required:
            return
        try:
            if not isinstance(version, str) or not version:
                raise ValueError
            Version(version)
        except (TypeError, ValueError):
            subject = reference or source
            self._problems.append(
                SpecificationProblem(
                    kind=SpecificationProblemKind.MALFORMED_VERSION,
                    severity=SpecificationProblemSeverity.ERROR,
                    source=source,
                    reference=reference,
                    message=(f"{subject.kind.value.capitalize()} {subject.id!r} has malformed version {version!r}"),
                )
            )

    @singledispatchmethod
    def _object_ref(self, value: object) -> SpecificationRef:
        raise TypeError(f"Unsupported specification type: {type(value).__name__}")

    @_object_ref.register(Requirement)
    def _(self, value: Requirement) -> SpecificationRef:
        return SpecificationRef(
            kind=SpecificationKind.REQUIREMENT,
            id=value.code,
            version=value.version,
            source_label=str(value.path) if value.path else None,
        )

    @_object_ref.register(RequirementRef)
    def _(self, value: RequirementRef) -> SpecificationRef:
        return SpecificationRef(
            kind=SpecificationKind.REQUIREMENT,
            id=value.code,
            version=value.version,
        )

    @_object_ref.register(Capability)
    def _(self, value: Capability) -> SpecificationRef:
        return SpecificationRef(
            kind=SpecificationKind.CAPABILITY,
            id=value.id,
            version=value.version,
            source_label=str(value.path) if value.path else None,
        )

    @_object_ref.register(Feature)
    def _(self, value: Feature) -> SpecificationRef:
        return SpecificationRef(
            kind=SpecificationKind.FEATURE,
            id=value.id,
            version=value.version,
            source_label=str(value.path) if value.path else None,
        )

    @_object_ref.register(FeatureRef)
    def _(self, value: FeatureRef) -> SpecificationRef:
        return SpecificationRef(
            kind=SpecificationKind.FEATURE,
            id=value.id,
            version=value.version,
        )

    @_object_ref.register(Profile)
    def _(self, value: Profile) -> SpecificationRef:
        return SpecificationRef(
            kind=SpecificationKind.PROFILE,
            id=value.id,
            version=value.version,
            source_label=str(value.path) if value.path else None,
        )
