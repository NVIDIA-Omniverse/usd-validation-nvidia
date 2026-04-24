# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import total_ordering
from typing import ClassVar

_SEMVER_PATTERN = (
    r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)
"""
Basic semantic versioning pattern: major.minor.patch[-prerelease][+build]
"""


@dataclass(frozen=True)
@total_ordering
class SemVer:
    LATEST: ClassVar[str] = "latest"
    DEFAULT: ClassVar[str] = "0.1.0"
    major: int = 0
    minor: int = 1
    patch: int = 0
    prerelease: str | None = None
    build: str | None = None

    def __init__(
        self,
        major: int | str | None = None,
        minor: int | None = None,
        patch: int | None = None,
        prerelease: str | None = None,
        build: str | None = None,
    ):
        match major:
            case str() if match := re.match(_SEMVER_PATTERN, major):
                if (minor, patch, prerelease, build) != (None, None, None, None):
                    raise ValueError("Cannot specify additional arguments when parsing a version string")
                major, minor, patch, prerelease, build = match.groups()
                major, minor, patch = int(major), int(minor), int(patch)
            case str():
                raise ValueError(f"Invalid version format: {major}. Expected semantic versioning format")
            case int():
                minor = minor if minor is not None else 0
                patch = patch if patch is not None else 0
            case None:
                major = 0
                minor = minor if minor is not None else 1
                patch = patch if patch is not None else 0
            case _:
                raise TypeError(f"Cannot create SemVer from {type(major)}")
        object.__setattr__(self, "major", major)
        object.__setattr__(self, "minor", minor)
        object.__setattr__(self, "patch", patch)
        object.__setattr__(self, "prerelease", prerelease)
        object.__setattr__(self, "build", build)

    def __lt__(self, other: SemVer) -> bool:
        # Compare major, minor, patch
        if (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch):
            return True
        elif (self.major, self.minor, self.patch) > (other.major, other.minor, other.patch):
            return False

        # If major.minor.patch are equal, compare prerelease
        if self.prerelease is None and other.prerelease is not None:
            return False  # self is greater
        elif self.prerelease is not None and other.prerelease is None:
            return True  # self is less
        elif self.prerelease is None and other.prerelease is None:
            return False  # equal
        else:
            return self.prerelease < other.prerelease

    def __repr__(self) -> str:
        version_str = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version_str += f"-{self.prerelease}"
        if self.build:
            version_str += f"+{self.build}"
        return version_str

    def __str__(self) -> str:
        return self.__repr__()

    def is_compatible(self, required_version: SemVer) -> bool:
        """
        Check if this version is compatible with the required version.
        Uses semantic versioning rules where major version changes indicate breaking changes.

        Args:
            required_version: Minimum required version

        Returns:
            True if this version is compatible, False otherwise
        """
        # Versions are only compatible if they have the same major version
        # and the current version is greater than or equal to the required version
        return self.major == required_version.major and self >= required_version
