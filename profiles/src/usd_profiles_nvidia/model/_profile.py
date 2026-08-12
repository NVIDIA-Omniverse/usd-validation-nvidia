# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from dataclasses import dataclass, field

from ._model import Model
from ._version import IdVersion


@dataclass(frozen=True, slots=True)
class ProfileFeature:
    """
    Represents a feature reference declared by a profile.

    Args:
        feature: The referenced feature id and version.
        optional: Whether the profile treats this feature as optional.
    """

    feature: IdVersion
    optional: bool = False


@dataclass(slots=True)
class Profile(Model):
    """
    Represents a profile.

    Args:
        features (list[ProfileFeature]): The feature references of the profile.
    """

    features: list[ProfileFeature] = field(default_factory=list)
