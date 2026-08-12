# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import re
from dataclasses import dataclass, replace
from typing import Any

from usd_profiles_nvidia.api import Feature, FeatureRef, Requirement, RequirementRef
from usd_profiles_nvidia.descriptors._features import feature_descriptor_errors
from usd_profiles_nvidia.model import IdVersion, Metadata, Version

from ._model import Section, Sections
from ._parser import walk_md
from ._references import ReferencesParser


class _FeatureParser(ReferencesParser):

    @property
    def default_name(self) -> str:
        return super().default_name.removeprefix("feature-")

    def _parse_attributes(self) -> dict[str, Any]:
        """
        Parse attributes from the document's first table.

        Returns:
            A dictionary of attribute key-value pairs.
        """
        data: dict[str, str] = self.main_table.to_dict()
        if "version" not in data:
            raise ValueError(f"Feature {self.relpath} has no version.")
        if "dependency" not in data:
            raise ValueError(f"Feature {self.relpath} has no dependency.")
        data["version"] = str(Version(data["version"]))
        if "dependencies" in data:
            data["dependencies"] = self._parse_dependencies(data["dependencies"])
        return data

    @staticmethod
    def _parse_dependencies(value: str) -> list[FeatureRef]:
        dependencies: list[FeatureRef] = []
        for token in re.split(r"[,\n]", value):
            token = token.strip()
            if token:
                dependency = IdVersion.parse(token)
                dependencies.append(
                    FeatureRef(dependency.id, str(dependency.version) if dependency.version is not None else None)
                )
        return dependencies

    def parse(self) -> Feature | None:
        """
        Parse the feature from the source file.
        Returns None if the feature has no requirements.
        """
        requirements: list[RequirementRef] = []
        if requirements_list := self.requirements_list:
            requirements.extend(
                RequirementRef(requirement.code, requirement.version)
                for requirement in requirements_list
            )
        elif requirements_table := self.requirements_table:
            requirements.extend(
                RequirementRef(requirement.code, requirement.version)
                for requirement in requirements_table
            )
        elif features_table := self.features_table:
            requirements.extend(features_table)
        if not requirements:
            return None
        attrs: dict[str, Any] = self._parse_attributes()
        return Feature(
            id=self.default_id,
            version=attrs["version"],
            requirements=requirements,
            dependencies=attrs.get("dependencies", []),
            path=Metadata(path=self.relpath).path,
        )


@dataclass
class FeatureParser:
    """
    Parser for a single feature.

    Args:
        root_dir: Sphinx srcdir.
        source_file: The file to parse features from.
    """

    root_dir: str
    source_file: str

    def parse(self) -> Feature | None:
        """
        Parse the feature from the source file.
        """
        return _FeatureParser(self.root_dir, self.source_file).parse()


@dataclass
class MultiFeatureParser(ReferencesParser):
    """
    Parser for a single feature with multiple versions.

    Args:
        root_dir: Sphinx srcdir.
        path: The path to the features directory.
    """

    @property
    def internal_id(self) -> str:
        try:
            attrs = self.main_table.to_dict()
        except ValueError:
            attrs = {}
        internal_id: str = attrs.get("internal id") or attrs.get("id") or self.default_id
        if internal_id.startswith("`") and internal_id.endswith("`"):
            internal_id = internal_id[1:-1]
        return internal_id

    def is_version_section(self, section: Section) -> bool:
        tokens: list[str] = section.title.split(" ", 1)
        if len(tokens) < 2 or tokens[0] != "Version":
            return False
        requirements_section: Section | None = section.sections.get("requirements")
        if requirements_section is None:
            return False
        if not requirements_section.bullets:
            return False
        return True

    @property
    def versions_section(self) -> Section | None:
        for section in self.main_section.walk_sections():
            subsections: Sections = section.sections
            if any(map(self.is_version_section, subsections)):
                return section
        return None

    def parse(self) -> list[Feature]:
        """
        Parse the feature from the source file.
        """
        versions_section: Section | None = self.versions_section
        if versions_section is None:
            return []
        feature: Feature = Feature(
            id=self.internal_id,
            version="",
            requirements=[],
            path=Metadata(path=self.relpath).path,
        )
        features: list[Feature] = []
        for section in filter(self.is_version_section, versions_section.sections):
            version: str = str(Version(section.title.split(" ")[1]))
            requirements_section: Section | None = section.sections.get("requirements")
            if requirements_section is None:
                continue
            requirements: list[Requirement] = self.get_requirements_list(requirements_section) or []
            requirement_refs: list[RequirementRef] = [
                RequirementRef(requirement.code, requirement.version)
                for requirement in requirements
            ]
            features.append(replace(feature, version=version, requirements=requirement_refs))
        return features


@dataclass
class MdFeaturesParser:
    """
    Markdown parser for features.

    Args:
        root_dir: Sphinx srcdir.
        path: The path to the features directory.
    """

    root_dir: str
    path: str

    def parse(self) -> list[Feature]:
        """
        Parse all features from the root directory.
        """
        features: list[Feature] = []
        for source_path in walk_md(self.path):
            with feature_descriptor_errors(source_path):
                if feature := FeatureParser(self.root_dir, source_path).parse():
                    features.append(feature)
                elif multi_feature := MultiFeatureParser(self.root_dir, source_path).parse():
                    features.extend(multi_feature)
        return features


FeaturesParser = MdFeaturesParser
