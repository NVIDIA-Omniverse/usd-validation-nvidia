# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import importlib.metadata
from functools import cache

__all__ = [
    "is_package_installed",
    "is_usd_available",
    "is_usd_distribution_conflict",
]


@cache
def is_package_installed(package_name: str) -> bool:
    """Return whether a package distribution is installed.

    Args:
        package_name: The Python package distribution name.

    Returns:
        Whether the package distribution metadata can be resolved.
    """
    try:
        importlib.metadata.distribution(package_name)
        return True
    except importlib.metadata.PackageNotFoundError:
        return False
    except Exception:
        return False


@cache
def is_usd_distribution_conflict() -> bool:
    """Return whether multiple USD provider distributions are installed.

    Returns:
        Whether both usd-core and usd-exchange distributions are installed.
    """
    return is_package_installed("usd-core") and is_package_installed("usd-exchange")


@cache
def is_usd_available() -> bool:
    """Return whether a provider for the pxr USD Python module is importable.

    Returns:
        Whether the pxr USD Python module can be imported.
    """
    try:
        import pxr as _pxr

        return _pxr is not None
    except ModuleNotFoundError as exc:
        if exc.name != "pxr":
            raise
        return False
