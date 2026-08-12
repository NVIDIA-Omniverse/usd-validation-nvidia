# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from typing import Any

from docutils import nodes
from sphinx.application import Sphinx


def oav_validator_link_role(
    name, rawtext, text, lineno, inliner, options={}, content=[]
) -> tuple[list[nodes.raw], list[nodes.raw]]:
    """
    USD Validation NVIDIA link role for specific versions.

    Example:

    .. code-block:: markdown
        {oav-validator-link}`aa-002`

    .. code-block:: rst
        :oav-validator-link:`aa-002`
    """
    raw_version, code = text.split("_")

    # Access Sphinx config through inliner
    config = inliner.document.settings.env.config
    base_url = config.oav_validator_base_url

    html = f'<a class="reference external" href="{base_url.rstrip("/")}/validation/docs/requirements.html#{code}"><span class="tag tag-nvidia">{raw_version}</span></a>'
    return [nodes.raw("", html, format="html")], []


def oav_validator_latest_link_role(
    name, rawtext, text, lineno, inliner, options={}, content=[]
) -> tuple[list[nodes.raw], list[nodes.raw]]:
    """
    USD Validation NVIDIA link role for the latest version.

    Example:

    .. code-block:: markdown
        {oav-validator-latest-link}`aa-002`

    .. code-block:: rst
        :oav-validator-latest-link:`aa-002`
    """
    # Access Sphinx config through inliner
    config = inliner.document.settings.env.config
    version = config.oav_validator_latest_version
    base_url = config.oav_validator_base_url

    code = text.strip()
    html = f'<a class="reference external" href="{base_url.rstrip("/")}/validation/docs/requirements.html#{code}"><span class="tag tag-nvidia">{version}+</span></a>'
    return [nodes.raw("", html, format="html")], []


def setup(app: Sphinx) -> dict[str, Any]:
    """
    Setup both USD Validation NVIDIA link roles.

    Args:
        app: The Sphinx application object.

    Returns:
        A dictionary containing the version of the extension.
    """
    app.add_config_value("oav_validator_latest_version", "latest", "env")
    app.add_config_value("oav_validator_base_url", "https://nvidia-omniverse.github.io/usd-validation-nvidia/", "env")
    app.add_role("oav-validator-link", oav_validator_link_role)
    app.add_role("oav-validator-latest-link", oav_validator_latest_link_role)
    return {
        "version": "0.1",
    }
