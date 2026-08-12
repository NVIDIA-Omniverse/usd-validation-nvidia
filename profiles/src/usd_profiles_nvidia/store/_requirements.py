# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from typing import Any

from usd_profiles_nvidia.api import Capability, Requirement, RequirementRef
from usd_profiles_nvidia.model import IdVersion, Version

from ._keystore import PersistentVersionedRegistry


class RequirementStore(PersistentVersionedRegistry[Requirement]):
    """
    A store of requirements.

    Args:
        directory: The directory to load requirements from.
    """

    def create_values(self, result: Any) -> list[Requirement]:
        if isinstance(result, Capability):
            return result.requirements
        return []

    def create_key(self, value: Any) -> IdVersion | None:
        if isinstance(value, Requirement):
            return IdVersion(value.code, Version(value.version) if value.version else None)
        return None

    def find_all(self, keys: list[RequirementRef]) -> list[Requirement]:
        result: list[Requirement] = []
        for key in keys:
            value: Requirement | None = self.find(IdVersion(key.code, Version(key.version) if key.version else None))
            if value is not None:
                result.append(value)
        return result
