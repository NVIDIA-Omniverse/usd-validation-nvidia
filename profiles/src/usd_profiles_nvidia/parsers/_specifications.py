# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import logging
import os
from dataclasses import dataclass
from typing import ClassVar

from usd_profiles_nvidia.api import Capability, Feature
from usd_profiles_nvidia.model import Profile, Specifications

from ._capabilities import CapabilitiesParser
from ._features import FeaturesParser
from ._profiles import ProfilesParser

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class SpecificationsParser:
    """
    Format-agnostic parser for specifications.

    Args:
        root_dir: Root directory containing capabilities/, profiles/, and features/ subdirectories.
                  If provided, capabilities_root, profiles_root, and features_root are derived from it.
        capabilities_root: Directory containing capability files. If None and root_dir is None, capabilities will be empty.
        profiles_root: Directory containing profile files. If None and root_dir is None, profiles will be empty.
        features_root: Directory containing feature files. If None and root_dir is None, features will be empty.
    """

    CAPABILITIES_DIRECTORY: ClassVar[str] = "capabilities"
    PROFILES_DIRECTORY: ClassVar[str] = "profiles"
    FEATURES_DIRECTORY: ClassVar[str] = "features"

    root_dir: str | None = None
    capabilities_root: str | None = None
    profiles_root: str | None = None
    features_root: str | None = None

    def __post_init__(self):
        if self.root_dir is not None:
            if self.capabilities_root is None:
                self.capabilities_root = os.path.join(self.root_dir, self.CAPABILITIES_DIRECTORY)

            if self.profiles_root is None:
                self.profiles_root = os.path.join(self.root_dir, self.PROFILES_DIRECTORY)

            if self.features_root is None:
                self.features_root = os.path.join(self.root_dir, self.FEATURES_DIRECTORY)

    def parse(self) -> Specifications:
        """
        Parse the specifications from the configured directories.
        """
        capabilities: list[Capability] = []
        if self.capabilities_root and os.path.exists(self.capabilities_root):
            capabilities = CapabilitiesParser(
                root_dir=self.root_dir or self.capabilities_root, path=self.capabilities_root
            ).parse()

        features: list[Feature] = []
        if self.features_root and os.path.exists(self.features_root):
            features = FeaturesParser(root_dir=self.root_dir or self.features_root, path=self.features_root).parse()

        profiles: list[Profile] = []
        if self.profiles_root and os.path.exists(self.profiles_root):
            profiles = ProfilesParser(root_dir=self.root_dir or self.profiles_root, path=self.profiles_root).parse()

        logger.info(f"Parsed {len(capabilities)} capabilities, {len(features)} features, {len(profiles)} profiles")
        return Specifications(
            capabilities=capabilities,
            features=features,
            profiles=profiles,
        )
