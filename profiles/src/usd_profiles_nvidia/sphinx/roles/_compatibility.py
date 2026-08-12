# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from typing import Any

from docutils import nodes
from sphinx.application import Sphinx

from usd_profiles_nvidia.model import Compatibility


def compatibility_role(
    name, rawtext, text, lineno, inliner, options={}, content=[]
) -> tuple[list[nodes.raw], list[nodes.raw]]:
    """
    Compatibility role for the OpenUSD Profiles.

    Example:

    .. code-block:: markdown
        - {compatibility}`OpenUSD`
        - {compatibility}`RTX`
        - {compatibility}`Kit`

    .. code-block:: rst
        .. compatibility:: openusd
        .. compatibility:: rtx
        .. compatibility:: kit

    """
    compat = Compatibility.from_name(text)
    html = f'<span class="tag {compat.style}" title="{compat.title}">{compat.display_name}</span>'
    return [nodes.raw("", html, format="html")], []


def setup(app: Sphinx) -> dict[str, Any]:
    """
    Setup the compatibility role.

    Args:
        app: The Sphinx application object.

    Returns:
        A dictionary containing the version of the extension.
    """
    app.add_role("compatibility", compatibility_role)
    return {
        "version": "0.1",
    }
