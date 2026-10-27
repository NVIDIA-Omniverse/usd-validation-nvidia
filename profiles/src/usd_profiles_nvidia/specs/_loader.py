# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from __future__ import annotations

import functools
import os
from dataclasses import dataclass, field
from pathlib import Path

from usd_profiles_nvidia.api import (
    Capability,
    Feature,
    Profile,
    Requirement,
    RequirementRef,
)
from usd_profiles_nvidia.descriptors import DescriptorKind
from usd_profiles_nvidia.descriptors._features import FeatureDescriptorEnricher
from usd_profiles_nvidia.descriptors._profiles import ProfileDescriptorEnricher
from usd_profiles_nvidia.descriptors._requirements import RequirementDescriptorEnricher
from usd_profiles_nvidia.parsers import (
    FeaturesParser,
    ProfilesParser,
    SpecificationsParser,
)

from ._diagnostics import _LoadedSpecificationsValidator
from ._types import SpecificationProblem


@dataclass(frozen=True)
class LoadedSpecifications:
    """Specifications loaded from authored descriptor files."""

    capabilities: list[Capability] = field(default_factory=list)
    features: list[Feature] = field(default_factory=list)
    profiles: list[Profile] = field(default_factory=list)

    @functools.cached_property
    def requirements(self) -> list[Requirement | RequirementRef]:
        """Return requirements and lazy references authored by loaded capabilities."""
        return [requirement for capability in self.capabilities for requirement in capability.requirements]

    def validate(self) -> tuple[SpecificationProblem, ...]:
        """Return local structural problems without resolving references or mutating loaded objects."""
        return _LoadedSpecificationsValidator(self).validate()


@dataclass(kw_only=True)
class SpecificationsLoader:
    """
    Load authored specification descriptors into public API DTOs.

    Args:
        root_dir: Root directory containing capabilities, profiles, and features.
        capabilities_root: Directory containing authored capabilities.
        profiles_root: Directory containing authored profiles.
        features_root: Directory containing authored features.
        features_roots: Additional feature descriptor files and/or directories.
        profiles_roots: Additional profile descriptor files and/or directories.
        reverse_domain: Prefix added to unqualified requirement references, profile IDs,
            and profile feature references after parsing.
    """

    root_dir: str | os.PathLike[str] | None = None
    capabilities_root: str | os.PathLike[str] | None = None
    profiles_root: str | os.PathLike[str] | None = None
    features_root: str | os.PathLike[str] | None = None
    features_roots: list[str | os.PathLike[str]] = field(default_factory=list)
    profiles_roots: list[str | os.PathLike[str]] = field(default_factory=list)
    reverse_domain: str = ""

    def load(self) -> LoadedSpecifications:
        """Load configured specifications without resolving their references."""
        parsed = SpecificationsParser(
            root_dir=self._as_string(self.root_dir),
            capabilities_root=self._as_string(self.capabilities_root),
            profiles_root=self._as_string(self.profiles_root),
            features_root=self._as_string(self.features_root),
        ).parse()

        features = list(parsed.features)
        for root_value in self.features_roots:
            root = self._validate_root(DescriptorKind.FEATURE, root_value, FeaturesParser.SUPPORTED_SUFFIXES)
            features.extend(FeaturesParser(root_dir=None, path=str(root)).parse())

        profiles = list(parsed.profiles)
        for root_value in self.profiles_roots:
            root = self._validate_root(DescriptorKind.PROFILE, root_value, ProfilesParser.SUPPORTED_SUFFIXES)
            profiles.extend(ProfilesParser(root_dir=None, path=str(root)).parse())

        feature_enricher = FeatureDescriptorEnricher(reverse_domain=self.reverse_domain)
        profile_enricher = ProfileDescriptorEnricher(reverse_domain=self.reverse_domain)
        requirement_enricher = RequirementDescriptorEnricher(reverse_domain=self.reverse_domain)
        return LoadedSpecifications(
            capabilities=[requirement_enricher.enrich_capability(capability) for capability in parsed.capabilities],
            features=[feature_enricher.enrich(feature) for feature in features],
            profiles=[profile_enricher.enrich(profile) for profile in profiles],
        )

    @staticmethod
    def _as_string(value: str | os.PathLike[str] | None) -> str | None:
        return os.fspath(value) if value is not None else None

    @staticmethod
    def _validate_root(
        descriptor_kind: DescriptorKind,
        root_value: str | os.PathLike[str],
        supported_suffixes: frozenset[str],
    ) -> Path:
        root = Path(root_value)
        kind_name = descriptor_kind.value
        if not root.exists():
            raise FileNotFoundError(f"{kind_name.capitalize()} root does not exist: {root}")
        if root.is_file() and root.suffix.lower() not in supported_suffixes:
            raise ValueError(f"Unsupported {kind_name} descriptor format: {root}")
        if not root.is_file() and not root.is_dir():
            raise ValueError(f"{kind_name.capitalize()} root is not a file or directory: {root}")
        return root
