# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from typing import Any

from sphinx.application import Sphinx

from usd_profiles_nvidia.sphinx.initialize import build_jsons_setup, build_specs_setup


def setup(app: Sphinx) -> dict[str, Any]:
    """
    Setup the Sphinx extension to build at initialization.

    Args:
        app: The Sphinx application object.

    Returns:
        A dictionary containing the version of the extension.
    """
    build_specs_setup(app)
    build_jsons_setup(app)
    return {
        "version": "1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
