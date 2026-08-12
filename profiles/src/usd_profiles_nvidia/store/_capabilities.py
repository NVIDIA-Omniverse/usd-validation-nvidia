# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from typing import Any

from usd_profiles_nvidia.api import Capability
from usd_profiles_nvidia.model import IdVersion, SimpleSpec, Version

from ._keystore import PersistentVersionedRegistry


class CapabilityStore(PersistentVersionedRegistry[Capability]):
    """
    A store of capabilities.

    Args:
        directory: The directory to load capabilities from.
    """

    def create_key(self, value: Any) -> IdVersion | None:
        if isinstance(value, Capability):
            return IdVersion(value.id, Version(value.version) if value.version else None)
        return None

    def get_by_spec(self, id_specifier: str) -> Capability | None:
        """
        Get a capability by its id and version specifier.

        Args:
            id_specifier: The id and version specifier to get the capability for.

        Returns:
            The capability if found, otherwise None.

        Examples:

        .. code-block:: python

            store = CapabilityStore("path/to/capabilities")
            capability = store.get_by_spec("atomic-asset>=0.2.0")
        """
        for key, capability in self.items():
            if not id_specifier.startswith(key.id):
                continue
            specifier = id_specifier[len(key.id) :]
            if key.version is not None and key.version in SimpleSpec(specifier):
                return capability
        return None
