# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from typing import Any

from docutils import nodes
from sphinx.application import Sphinx


def manual_validation_role(
    name, rawtext, text, lineno, inliner, options={}, content=[]
) -> tuple[list[nodes.raw], list[nodes.raw]]:
    """
    Manual validation role for the OpenUSD Profiles.

    Example:

    .. code-block:: markdown
        - {manual-validation}`manual-validation-required`

    .. code-block:: rst
        .. manual-validation:: manual-validation-required
    """
    html = '<span class="tag tag-nvidia">Manual</span>'
    node = nodes.raw("", html, format="html")
    return [node], []


def setup(app: Sphinx) -> dict[str, Any]:
    """
    Setup the manual validation role.

    Args:
        app: The Sphinx application object.

    Returns:
        A dictionary containing the version of the extension.
    """
    app.add_role("manual-validation", manual_validation_role)
    return {
        "version": "0.1",
    }
