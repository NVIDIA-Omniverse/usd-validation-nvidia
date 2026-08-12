# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from usd_profiles_nvidia.api import Feature
from usd_profiles_nvidia.descriptors._features import FeatureDescriptorEnricher
from usd_profiles_nvidia.parsers import FeaturesParser


@dataclass(frozen=True)
class LoadedSpecifications:
    """
    Specifications loaded from authored descriptor files.

    Args:
        features: Authored feature definitions. Requirement and feature relationships
            remain references and are not resolved against runtime registries.
    """

    features: list[Feature] = field(default_factory=list)


@dataclass(kw_only=True)
class SpecificationsLoader:
    """
    Load authored specification descriptors into public API DTOs.

    Args:
        features_roots: Feature descriptor files and/or directories. Directories
            are searched recursively for Markdown, JSON, and TOML files.
        reverse_domain: Prefix added to unqualified requirement references after parsing.
    """

    features_roots: list[str | os.PathLike[str]] = field(default_factory=list)
    reverse_domain: str = ""

    def load(self) -> LoadedSpecifications:
        """Load configured feature descriptors without resolving their references."""
        features: list[Feature] = []
        for root_value in self.features_roots:
            root = self._validate_feature_root(root_value)
            features.extend(FeaturesParser(root_dir=None, path=str(root)).parse())

        enricher = FeatureDescriptorEnricher(reverse_domain=self.reverse_domain)
        return LoadedSpecifications(features=[enricher.enrich(feature) for feature in features])

    @staticmethod
    def _validate_feature_root(root_value: str | os.PathLike[str]) -> Path:
        root = Path(root_value)
        if not root.exists():
            raise FileNotFoundError(f"Feature root does not exist: {root}")
        if root.is_file() and root.suffix.lower() not in FeaturesParser.SUPPORTED_SUFFIXES:
            raise ValueError(f"Unsupported feature descriptor format: {root}")
        if not root.is_file() and not root.is_dir():
            raise ValueError(f"Feature root is not a file or directory: {root}")
        return root
