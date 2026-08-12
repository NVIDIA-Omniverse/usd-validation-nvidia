# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import os
from typing import Any

from sphinx.application import Sphinx
from sphinx.config import Config


def add_static_files(app: Sphinx, config: Config) -> None:
    """
    Add static files to the Sphinx application.

    Args:
        app: The Sphinx application object.
        config: The Sphinx configuration object.
    """
    config.html_static_path.append(os.path.join(os.path.dirname(__file__), "_static"))


def setup(app: Sphinx) -> dict[str, Any]:
    """
    Setup the Sphinx extension to add static files.

    Args:
        app: The Sphinx application object.

    Returns:
        A dictionary containing the version of the extension.
    """
    app.connect("config-inited", add_static_files)
    return {
        "version": "1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
