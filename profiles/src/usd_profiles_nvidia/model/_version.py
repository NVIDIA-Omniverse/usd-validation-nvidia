# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import singledispatchmethod


@dataclass(init=False, frozen=True, order=True, slots=True)
class Version:
    """
    Represents a version supporting semver (``"1.0.0"``), integer-only (``"1"``), and underscore (``"23_05"``) formats.

    ``str()`` preserves the original input format. Equality and ordering use only ``(major, minor, patch)``.
    """

    major: int
    minor: int
    patch: int
    source_str: str = field(compare=False, hash=False, repr=False)

    @singledispatchmethod
    def __init__(self, arg) -> None:
        raise TypeError(f"Cannot create Version from {type(arg)}")

    @__init__.register
    def _(self, version: str) -> None:
        tokens = version.split(".")
        if len(tokens) == 3:
            # Semver: "1.0.0"
            object.__setattr__(self, "major", int(tokens[0]))
            object.__setattr__(self, "minor", int(tokens[1]))
            object.__setattr__(self, "patch", int(tokens[2]))
        elif len(tokens) == 1:
            # Integer-only ("1") or underscore ("23_05")
            parts = tokens[0].split("_")
            object.__setattr__(self, "major", int(parts[0]))
            object.__setattr__(self, "minor", int(parts[1]) if len(parts) > 1 else 0)
            object.__setattr__(self, "patch", int(parts[2]) if len(parts) > 2 else 0)
        else:
            raise ValueError(f"Invalid version string: {version}")
        object.__setattr__(self, "source_str", version)

    @__init__.register
    def _(self, major: int, minor: int, patch: int) -> None:
        object.__setattr__(self, "major", major)
        object.__setattr__(self, "minor", minor)
        object.__setattr__(self, "patch", patch)
        object.__setattr__(self, "source_str", f"{major}.{minor}.{patch}")

    def __str__(self) -> str:
        return self.source_str


@Version.__init__.register(Version)
def _(self: Version, other: Version) -> None:
    object.__setattr__(self, "major", other.major)
    object.__setattr__(self, "minor", other.minor)
    object.__setattr__(self, "patch", other.patch)
    object.__setattr__(self, "source_str", other.source_str)


@dataclass(frozen=True, slots=True)
class SimpleSpec:
    """
    Represents a simple version specifier.

    Args:
        spec (str): The version specifier string (e.g. ``">=1.0.0"``).
    """

    spec: str

    def __contains__(self, other: Version) -> bool:
        if self.spec.startswith(">="):
            return other >= Version(self.spec[2:])
        elif self.spec.startswith(">"):
            return other > Version(self.spec[1:])
        elif self.spec.startswith("<="):
            return other <= Version(self.spec[2:])
        elif self.spec.startswith("<"):
            return other < Version(self.spec[1:])
        elif self.spec.startswith("=="):
            return other == Version(self.spec[2:])
        else:
            return other == Version(self.spec)

    def __str__(self) -> str:
        return self.spec

    def __repr__(self) -> str:
        return f"SimpleSpec({self.spec})"


# Matches .vN or .vN_N at the end of an identifier
_DOT_V_PATTERN = re.compile(r"\.v(\d+(?:_\d+)*)$")


@dataclass(frozen=True, order=True, slots=True)
class IdVersion:
    id: str
    version: Version | None = None

    @classmethod
    def parse(cls, id_version: str) -> IdVersion:
        """Parse a versioned identifier string.

        Formats: ``.vN``/``.vN_N`` suffix (priority), ``@semver`` separator, or bare id (version=None).

        Args:
            id_version: String to parse (e.g. ``"com.nvidia.usd.geometry.v1"``, ``"VG.001@1.0.0"``, ``"VG.001"``).

        Returns:
            An ``IdVersion`` with the extracted id and version, or ``version=None`` if no version is present.
        """
        # .vN suffix: "com.nvidia.usd.geometry.v1" -> ("com.nvidia.usd.geometry", Version("1"))
        if m := _DOT_V_PATTERN.search(id_version):
            return IdVersion(id_version[: m.start()], Version(m.group(1)))
        # @ separator: "VG.001@1.0.0" -> ("VG.001", Version("1.0.0"))
        tokens: list[str] = [token.strip() for token in id_version.split("@")]
        if len(tokens) == 1:
            return IdVersion(tokens[0], None)
        elif len(tokens) == 2:
            return IdVersion(tokens[0], Version(tokens[1]))
        else:
            raise ValueError(f"Invalid id version string: {id_version}")
