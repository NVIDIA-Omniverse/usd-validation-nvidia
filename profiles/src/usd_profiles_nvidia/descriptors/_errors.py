# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from enum import Enum


class DescriptorKind(str, Enum):
    """Supported authored descriptor kinds."""

    FEATURE = "feature"
    PROFILE = "profile"


class DescriptorError(ValueError):
    """An invalid descriptor with its kind and source path."""

    def __init__(self, kind: DescriptorKind, path: str | os.PathLike[str], error: Exception):
        self.kind = kind
        self.path = os.fspath(path)
        self.original_error = error
        super().__init__(f"Invalid {kind.value} descriptor {self.path}: {error}")


@contextmanager
def descriptor_errors(kind: DescriptorKind, path: str | os.PathLike[str]) -> Iterator[None]:
    """Add descriptor-kind and source-path context to expected parsing errors."""
    try:
        yield
    except DescriptorError:
        raise
    except (KeyError, TypeError, ValueError) as error:
        raise DescriptorError(kind, path, error) from error
