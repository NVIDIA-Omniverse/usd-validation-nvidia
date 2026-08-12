# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from dataclasses import dataclass

from usd_profiles_nvidia.markdown import MdProfilesParser
from usd_profiles_nvidia.model import Profile
from usd_profiles_nvidia.toml import TomlProfilesParser


@dataclass
class ProfilesParser:
    """
    Format-agnostic parser for all profiles in the root directory.

    Aggregates individual ``profile-*.md`` files and ``profiles.toml`` when
    both sources are present.

    Args:
        root_dir: Sphinx srcdir.
        path: The path to the profiles directory.
    """

    root_dir: str
    path: str

    def parse(self) -> list[Profile]:
        """
        Parse all profiles from Markdown and TOML sources.
        """
        profiles: list[Profile] = MdProfilesParser(root_dir=self.root_dir, path=self.path).parse()
        profiles.extend(TomlProfilesParser(root_dir=self.root_dir, path=self.path).parse())
        return profiles
