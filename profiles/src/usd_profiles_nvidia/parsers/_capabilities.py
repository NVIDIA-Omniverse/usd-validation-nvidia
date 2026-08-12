# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from dataclasses import dataclass

from usd_profiles_nvidia.api import Capability
from usd_profiles_nvidia.markdown import MdCapabilitiesParser


@dataclass
class CapabilitiesParser:
    """
    Format-agnostic parser for all capabilities in the root directory.

    Args:
        root_dir: Sphinx srcdir.
        path: The path to the capabilities directory.
    """

    root_dir: str
    path: str

    def parse(self) -> list[Capability]:
        """
        Parse all capabilities from the root directory.
        """
        return MdCapabilitiesParser(root_dir=self.root_dir, path=self.path).parse()
