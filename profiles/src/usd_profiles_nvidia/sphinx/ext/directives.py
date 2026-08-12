# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from typing import Any

from sphinx.application import Sphinx

from usd_profiles_nvidia.sphinx.directives import (
    features_table_setup,
    requirements_table_setup,
)


def setup(app: Sphinx) -> dict[str, Any]:
    """
    Setup the Sphinx extension to generate requirement tables.

    Args:
        app: The Sphinx application object.

    Returns:
        A dictionary containing the version of the extension.
    """
    requirements_table_setup(app)
    features_table_setup(app)
    return {
        "version": "1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
