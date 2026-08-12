# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from __future__ import annotations

import re
from enum import Enum


class Compatibility(Enum):
    """
    Compatibility levels for requirements.
    """

    COREUSD = ("core-usd", "Compatible with OpenUSD", "tag-openUSD")
    OPENUSD = ("open-usd", "Compatible with OpenUSD", "tag-openUSD")
    RTX = ("rtx", "Compatible with NVIDIA Omniverse RTX", "tag-nvidia")
    KIT = ("kit", "Compatible with NVIDIA Omniverse Kit", "tag-nvidia")
    KIT_107 = ("kit-107+", "Compatible with NVIDIA Omniverse Kit 1.0.7", "tag-nvidia")
    PHYSX = ("physx", "Compatible with NVIDIA PhysX", "tag-nvidia")
    OMNIVERSE = ("omniverse", "Compatible with NVIDIA Omniverse", "tag-nvidia")
    OTHER = ("other", "Compatible with other software", "tag-compatibility")

    def __init__(self, display_name: str, title: str, style: str):
        self.display_name = display_name
        self.title = title
        self.style = style

    @classmethod
    def from_name(cls, display_name: str) -> Compatibility:
        """Get a Compatibility by its display name (case-insensitive), returns OTHER if not found."""
        aliases: dict[str, Compatibility] = {c.display_name: c for c in cls}
        aliases.update(
            {
                "core usd": cls.COREUSD,
                "openusd": cls.OPENUSD,
                "open usd": cls.OPENUSD,
                "kit-107.0+": cls.KIT_107,
                "nvidia-omniverse": cls.OMNIVERSE,
                "nvidia omniverse": cls.OMNIVERSE,
            }
        )
        return aliases.get(display_name.lower(), cls.OTHER)

    @classmethod
    def from_role(cls, role: str) -> Compatibility:
        """Get a Compatibility from a role string like {compatibility}`OpenUSD`, returns OTHER if not found."""
        match = re.search(r"\{compatibility\}`([^`]+)`", role)
        return cls.from_name(match.group(1)) if match else cls.OTHER
