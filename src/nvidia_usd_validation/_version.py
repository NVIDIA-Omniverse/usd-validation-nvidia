# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from importlib.metadata import PackageNotFoundError, version as _metadata_version

__all__ = [
    "__version__",
    "get_version",
]

# Version used when distribution metadata is unavailable, such as source-tree or stripped-metadata environments.
_DEFAULT_VERSION = "1.18.0"

# Distribution name from pyproject.toml; this differs from the import package name.
_PACKAGE_NAME = "nvidia-usd-validation"


def get_version():
    """Returns the version of this module."""
    try:
        return _metadata_version(_PACKAGE_NAME) or _DEFAULT_VERSION
    except PackageNotFoundError:
        return _DEFAULT_VERSION


__version__ = get_version()
