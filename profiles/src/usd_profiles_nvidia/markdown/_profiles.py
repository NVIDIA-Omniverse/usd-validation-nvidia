# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import logging
import os
from dataclasses import dataclass

from usd_profiles_nvidia.model import (
    IdVersion,
    Metadata,
    Naming,
    Profile,
    ProfileFeature,
    Version,
)

from ._features import FeatureParser
from ._parser import FileParser, walk_md

logger = logging.getLogger(__name__)


class _ProfileTreeProcessor(FileParser):

    def _parse_id(self, document) -> str:
        """
        Parse the id from the document.
        """
        return Naming.identifier(self.title)

    def _parse_features(self, document) -> list[ProfileFeature]:
        """
        Parse the features from the document.
        """
        if len(document.sections) != 1:
            raise ValueError(f"Profile {self.relpath} has more than one section.")
        if document.sections[0].sections.get("features") is None:
            raise ValueError(f"Profile {self.relpath} has no features section.")
        features: list[ProfileFeature] = []
        for bullet_list in document.sections[0].sections.get("features").bullets:
            for bullet in bullet_list:
                for link in bullet.links:
                    feature_path: str = os.path.normpath(os.path.join(os.path.dirname(self.source_file), link.href))
                    if not feature_path.startswith(os.path.normpath(self.root_dir)):
                        raise ValueError(
                            f"Profile {self.relpath} references feature {link.href} which is outside documentation."
                        )
                    if not os.path.exists(feature_path):
                        raise ValueError(f"Profile {self.relpath} references feature {link.href} which does not exist.")
                    if feature := FeatureParser(self.root_dir, feature_path).parse():
                        # Markdown profile links do not currently encode optionality; TOML profiles can set it.
                        features.append(
                            ProfileFeature(IdVersion(feature.id, Version(feature.version) if feature.version else None))
                        )
        return features

    def run(self) -> Profile:
        document = self.document
        return Profile(
            id=self._parse_id(document),
            version=str(self.default_version),
            display_name=self.title,
            message=self.description,
            features=self._parse_features(document),
            metadata=Metadata(path=self.relpath),
        )


@dataclass
class MdProfilesParser:
    """
    Markdown parser for all profiles in the root directory.

    Args:
        root_dir: Sphinx srcdir.
        path: The path to the profiles directory.
    """

    root_dir: str
    path: str

    def _parse_md(self, source_path: str) -> Profile:
        logger.info(f"Parsing profile from: {source_path}")
        return _ProfileTreeProcessor(self.root_dir, source_path).run()

    def parse(self) -> list[Profile]:
        """
        Parse all Markdown profiles from the root directory.
        """
        profiles: list[Profile] = []
        for full_path in walk_md(self.path):
            source_file = os.path.basename(full_path)
            if source_file.endswith("profiles.md"):
                continue
            if not source_file.startswith("profile-"):
                continue
            if profile := self._parse_md(full_path):
                profiles.append(profile)
        return profiles


ProfilesParser = MdProfilesParser
