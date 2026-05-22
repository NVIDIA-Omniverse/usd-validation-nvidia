# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
__all__ = [
    "__version__",
    "get_version",
]

__version__ = "1.19.2"


def get_version():
    """Returns the version of this module."""
    return __version__
