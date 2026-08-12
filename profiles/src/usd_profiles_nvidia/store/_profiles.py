# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from typing import Any

from usd_profiles_nvidia.model import IdVersion, Profile, Version

from ._keystore import PersistentVersionedRegistry


class ProfileStore(PersistentVersionedRegistry[Profile]):
    """
    A store of profiles.

    Args:
        directory: The directory to load profiles from.
    """

    def create_key(self, value: Any) -> IdVersion | None:
        if isinstance(value, Profile):
            return IdVersion(value.id, Version(value.version) if value.version else None)
        return None
