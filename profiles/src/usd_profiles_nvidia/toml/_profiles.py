# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import logging
import os
from dataclasses import dataclass

from usd_profiles_nvidia.model import (
    IdVersion,
    Metadata,
    Profile,
    ProfileFeature,
    Version,
)

PROFILES_TOML = "profiles.toml"

logger = logging.getLogger(__name__)


@dataclass
class _TomlProfilesParser:
    """
    Parser for profiles defined in a TOML file.

    The TOML format maps profile names to versioned feature sets::

        [Profile-Name]
        "1.0.0" = {features = [
            {"FEATURE_ID" = {version = "0.1.0"}, optional = true},
        ]}
        "2.0.0" = {features = [
            {"FEATURE_ID" = {version = "1.0.0"}},
        ]}

    Each TOML table is a profile name; keys within are version strings
    mapping to a dict with a ``features`` list. Each feature entry maps a
    feature ID to ``{version = "X.Y.Z"}`` and may include ``optional = true``.

    Args:
        toml_path: Path to the profiles.toml file.
    """

    toml_path: str

    @staticmethod
    def _parse_feature_entry(entry: dict) -> ProfileFeature:
        """Parse a single feature entry like ``{"FET001" = {version = "0.1.0"}, optional = true}``."""
        feature_entry = entry.copy()
        optional = feature_entry.pop("optional", False)
        if len(feature_entry) != 1:
            raise ValueError(f"Expected exactly one feature key per entry, got: {list(entry.keys())}")
        feature_id, attrs = next(iter(feature_entry.items()))
        version = Version(attrs["version"])
        return ProfileFeature(IdVersion(feature_id, version), optional=optional)

    def parse(self) -> list[Profile]:
        """Parse all profiles and versions from the TOML file."""
        # tomllib is stdlib in Python 3.11+; fall back to tomli for 3.10
        try:
            import tomllib
        except ModuleNotFoundError:
            import tomli as tomllib

        if not os.path.exists(self.toml_path):
            raise FileNotFoundError(f"Profiles TOML file not found: {self.toml_path}")

        with open(self.toml_path, "rb") as f:
            data = tomllib.load(f)

        # Validate structure strictly — profiles.toml is authored by humans
        # and any structural error should fail fast rather than produce
        # silently incomplete output.
        profiles: list[Profile] = []
        relpath = os.path.basename(self.toml_path)
        for profile_name, versions in data.items():
            if not isinstance(versions, dict):
                raise ValueError(
                    f"Profile '{profile_name}' must be a TOML table, got {type(versions).__name__}: {versions!r}"
                )
            for version_str, version_data in versions.items():
                version = str(Version(version_str))
                if not isinstance(version_data, dict):
                    raise ValueError(
                        f"Profile '{profile_name}' version '{version_str}' must be a table, "
                        f"got {type(version_data).__name__}: {version_data!r}"
                    )
                if "features" not in version_data:
                    raise ValueError(
                        f"Profile '{profile_name}' version '{version_str}' missing required 'features' key"
                    )
                features: list[ProfileFeature] = []
                for entry in version_data["features"]:
                    features.append(self._parse_feature_entry(entry))
                # Use the raw TOML table name as the profile id (not normalized).
                # This preserves the original casing (e.g. "Robot-Body-Isaac")
                # for CLI --profile matching and user-facing output.
                profiles.append(
                    Profile(
                        id=profile_name,
                        version=version,
                        display_name=profile_name,
                        features=features,
                        metadata=Metadata(path=relpath),
                    )
                )
        return profiles


@dataclass
class TomlProfilesParser:
    """
    Directory-level parser for TOML profiles.

    Args:
        root_dir: Sphinx srcdir.
        path: The path to the profiles directory.
    """

    root_dir: str
    path: str

    def parse(self) -> list[Profile]:
        """
        Parse all TOML profiles from the root directory.
        """
        toml_path = os.path.join(self.path, PROFILES_TOML)
        if not os.path.exists(toml_path):
            return []
        logger.info(f"Parsing profiles from TOML: {toml_path}")
        return _TomlProfilesParser(toml_path).parse()
