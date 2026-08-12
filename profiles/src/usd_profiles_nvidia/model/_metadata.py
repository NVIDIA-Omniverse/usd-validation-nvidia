# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import os
from typing import Protocol, runtime_checkable


class Metadata:
    """
    Represents the metadata of a model.

    Args:
        path (str): The path to the model in the documentation
    """

    def __init__(self, path: str = ""):
        self.path = path

    @property
    def path(self) -> str:
        return self._path

    @path.setter
    def path(self, value: str) -> None:
        value = value.replace(os.sep, "/")
        value = value.removeprefix("/")
        self._path, _ = os.path.splitext(value)

    @property
    def html_path(self) -> str:
        return self.path + ".html"

    @property
    def md_path(self) -> str:
        return self.path + ".md"


@runtime_checkable
class HasMetadata(Protocol):
    """
    A protocol for models that have metadata.

    Args:
        metadata (Metadata): The metadata of the model.
    """

    metadata: Metadata
