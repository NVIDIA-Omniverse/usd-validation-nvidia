# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from __future__ import annotations

import re
from collections.abc import Sequence
from enum import Enum


class Tag(Enum):
    """
    Tags for requirements.

    Args:
        display_name: The display name of the tag
        emoji: The emoji of the tag
        title: The title of the tag
        priority: The sorting priority (lower = higher priority)
    """

    ESSENTIAL = ("essential", "🔑", "Essential Requirement", 0)
    CORRECTNESS = ("correctness", "✅", "Correctness Requirement", 1)
    LIMITATION = ("limitation", "⛔", "Limitation of the 'compatible' software", 2)
    HIGH_QUALITY = ("high-quality", "💎", "High Quality Recommendation", 3)
    PERFORMANCE = ("performance", "🚀", "Performance Recommendation", 4)
    UNKNOWN = ("unknown", "❓", "Unknown Tag", 0)

    def __init__(self, display_name: str, emoji: str, title: str, priority: int):
        self.display_name = display_name
        self.emoji = emoji
        self.title = title
        self.priority = priority

    @classmethod
    def from_name(cls, display_name: str) -> Tag:
        """Get a Tag by its display name (case-insensitive), returns UNKNOWN if not found."""
        aliases: dict[str, Tag] = {tag.display_name: tag for tag in cls}
        aliases.update(
            {
                "core": cls.ESSENTIAL,
                "high quality": cls.HIGH_QUALITY,
                "highquality": cls.HIGH_QUALITY,
            }
        )
        return aliases.get(display_name.lower(), cls.UNKNOWN)

    @classmethod
    def from_role(cls, role: str) -> Tag:
        """Get a Tag from a role string like {tag}`performance`, returns UNKNOWN if not found."""
        match = re.search(r"\{tag\}`([^`]+)`", role)
        return cls.from_name(match.group(1)) if match else cls.UNKNOWN


def tag_priority(tags: Sequence[str]) -> int:
    return min((Tag.from_name(tag).priority for tag in tags), default=0)
