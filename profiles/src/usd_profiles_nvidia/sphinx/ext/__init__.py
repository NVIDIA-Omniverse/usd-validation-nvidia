# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from typing import Any

from sphinx.application import Sphinx

from .directives import setup as directives_setup
from .initialize import setup as initialize_setup
from .roles import setup as roles_setup
from .static import setup as static_setup


def setup(app: Sphinx) -> dict[str, Any]:
    """
    Setup all available extensions. This includes:
    - initialize: Setup the Sphinx extension to build at initialization.
    - roles: Setup all available roles.
    - static: Setup the Sphinx extension to add static files.
    - directives: Setup the Sphinx extension to generate requirement tables.

    Args:
        app: The Sphinx application object.

    Returns:
        A dictionary containing the version of the extension.
    """
    initialize_setup(app)
    roles_setup(app)
    static_setup(app)
    directives_setup(app)
    return {
        "version": "1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
