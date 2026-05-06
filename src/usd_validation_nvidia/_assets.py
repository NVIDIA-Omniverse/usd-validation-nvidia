# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from pxr import Usd

from ._results import Results

__all__ = [
    "AssetLocatedCallback",
    "AssetProgress",
    "AssetProgressCallback",
    "AssetType",
    "AssetValidatedCallback",
]

AssetType = str | Usd.Stage
"""
 A typedef for the assets that ValidationEngine can process.
 When it is a `str`, it is expected to be an URI that can be accessed.
 When it is a `Usd.Stage`, it will be validated directly without ever locating a file on disk/server.
 Note using a live Stage necessarily bypasses some validations (i.e. file I/O checks)
"""


@dataclass(frozen=True)
class AssetProgress:
    """
    Keeps track of the progress for a particular asset.

    Attributes:
        asset (str): The identifier of the asset, i.e. the result of Usd.Describe.
        progress (float): The percent of progress (between 0 and 1, both inclusive).
        results (Results | None): The partial results for the asset.
    """

    asset: str
    progress: float
    results: Results | None = None


@runtime_checkable
class AssetLocatedCallback(Protocol):
    """
    A typedef for the notification of asset(s) founds during :py:meth:`ValidationEngine.validate_with_callbacks`.
    It is invoked at the beginning of asset validation.

    Args:
        asset (AssetType): The asset type located.
    """

    def __call__(self, asset: AssetType) -> None: ...


@runtime_checkable
class AssetValidatedCallback(Protocol):
    """
    A typedef for the notification of asset results found during :py:meth:`ValidationEngine.validate_with_callbacks`.

    Args:
        results (Results): The results for a specific asset.
    """

    def __call__(self, results: Results) -> None: ...


@runtime_checkable
class AssetProgressCallback(Protocol):
    """
    A typedef for the notification of asset progress found during :py:meth:`ValidationEngine.validate_with_callbacks`.

    Args:
        progress (AssetProgress): The progress for a specific asset.
    """

    def __call__(self, progress: AssetProgress) -> None: ...
