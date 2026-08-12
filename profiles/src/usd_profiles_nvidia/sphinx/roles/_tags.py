# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from typing import Any

from docutils import nodes
from sphinx.application import Sphinx

from usd_profiles_nvidia.model import Tag


def tag_role(name, rawtext, text, lineno, inliner, options={}, content=[]) -> tuple[list[nodes.raw], list[nodes.raw]]:
    """
    Tag role for the OpenUSD Profiles.

    Example:

    .. code-block:: markdown
        - {tag}`performance`
        - {tag}`high-quality`
        - {tag}`correctness`
        - {tag}`essential`
        - {tag}`limitation`

    .. code-block:: rst
        .. tag:: performance
        .. tag:: high-quality
        .. tag:: correctness
        .. tag:: essential
        .. tag:: limitation
        .. tag:: performance
    """
    tag = Tag.from_name(text)
    html = f'<span class="emoji-tag" title="{tag.title}">{tag.emoji}</span>'
    return [nodes.raw("", html, format="html")], []


def setup(app: Sphinx) -> dict[str, Any]:
    """
    Setup the tag role.

    Args:
        app: The Sphinx application object.

    Returns:
        A dictionary containing the version of the extension.
    """
    app.add_role("tag", tag_role)
    return {
        "version": "0.1",
    }
