# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from usd_profiles_nvidia.api import Profile
from usd_profiles_nvidia.descriptors._errors import DescriptorKind, descriptor_errors
from usd_profiles_nvidia.descriptors._profiles import ProfileDescriptorDecoder
from usd_profiles_nvidia.markdown import MdProfilesParser

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


@dataclass
class ProfilesParser:
    """
    Format-agnostic parser for all profiles in the root directory.

    Parses profile descriptor files into public API DTOs. Markdown feature
    links are resolved, while JSON and TOML feature references remain refs.

    Args:
        root_dir: Sphinx srcdir. Inferred from path when None.
        path: The path to a profile file or directory.
    """

    SUPPORTED_SUFFIXES: ClassVar[frozenset[str]] = frozenset({".md", ".json", ".toml"})

    root_dir: str | None
    path: str

    def parse(self) -> list[Profile]:
        """
        Parse all profiles from the configured file or directory.
        """
        path = Path(self.path)
        if path.is_file():
            return self._parse_file(path, Path(self.root_dir) if self.root_dir else path.parent)
        if not path.is_dir():
            raise FileNotFoundError(f"Profile path does not exist: {path}")

        root_dir = Path(self.root_dir) if self.root_dir else path
        profiles = self._parse_markdown(path, root_dir)
        descriptor_paths = sorted(
            (
                descriptor_path
                for descriptor_path in path.rglob("*")
                if descriptor_path.is_file()
                and descriptor_path.name != "pyproject.toml"
                and descriptor_path.suffix.lower() in {".json", ".toml"}
            ),
            key=lambda descriptor_path: descriptor_path.relative_to(path).as_posix(),
        )
        for descriptor_path in descriptor_paths:
            profiles.extend(self._parse_file(descriptor_path, root_dir))
        return profiles

    @staticmethod
    def _parse_file(path: Path, root_dir: Path) -> list[Profile]:
        suffix = path.suffix.lower()
        if suffix == ".md":
            return ProfilesParser._parse_markdown(path.parent, root_dir, source_path=path)
        if suffix not in {".json", ".toml"}:
            raise ValueError(f"Unsupported profile descriptor format: {path}")

        decoder = ProfileDescriptorDecoder()
        relative_path = path.relative_to(root_dir).as_posix()
        with descriptor_errors(DescriptorKind.PROFILE, path):
            if suffix == ".json":
                with path.open(encoding="utf-8") as descriptor_file:
                    data = json.load(descriptor_file)
            else:
                with path.open("rb") as descriptor_file:
                    data = tomllib.load(descriptor_file)
            return decoder.decode_all(data, path=relative_path)

    @staticmethod
    def _parse_markdown(path: Path, root_dir: Path, *, source_path: Path | None = None) -> list[Profile]:
        profiles = MdProfilesParser(root_dir=str(root_dir), path=str(path)).parse()
        if source_path is not None:
            source_relative_path = source_path.relative_to(root_dir).with_suffix("").as_posix()
            profiles = [profile for profile in profiles if profile.path == source_relative_path]
        return profiles
