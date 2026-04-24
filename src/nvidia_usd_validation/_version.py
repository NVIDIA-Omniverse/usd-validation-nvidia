# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from importlib.metadata import version as _metadata_version

__all__ = [
    "__version__",
    "get_version",
]

__version__ = _metadata_version("nvidia-usd-validation")


def get_version():
    """Returns the version of this module."""
    return __version__
