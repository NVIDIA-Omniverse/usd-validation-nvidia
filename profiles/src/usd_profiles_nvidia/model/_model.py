# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import os
from dataclasses import dataclass, field

from ._metadata import Metadata
from ._naming import Naming


@dataclass(slots=True, kw_only=True)
class Model:
    """
    Represents a model.

    Args:
        id: The id of the model.
        version: The version of the model.
        display_name: The display name of the model.
        message: The message of the model.
    """

    id: str = ""
    version: str | None = None
    display_name: str | None = None
    message: str | None = None
    metadata: Metadata = field(default_factory=Metadata)
    namespace: str = ""

    @property
    def namespaced_id(self) -> str:
        """Return ``id`` qualified with ``namespace`` prefix, or ``id`` unchanged if already qualified or namespace is empty."""
        if not self.namespace or not self.id:
            return self.id
        prefix: str = f"{self.namespace.rstrip('.')}."
        return self.id if self.id.startswith(prefix) else f"{prefix}{self.id}"

    @property
    def enum_id(self) -> str:
        return Naming.enum_name(self.id, namespace=self.namespace)

    @property
    def enum_id_version(self) -> str:
        return Naming.enum_name(self.id, self.version, namespace=self.namespace)

    @property
    def class_name(self) -> str:
        return Naming.class_name(self.id, namespace=self.namespace)

    @property
    def source_file_name(self) -> str:
        filename = os.path.basename(self.metadata.path)
        return os.path.splitext(filename)[0]
