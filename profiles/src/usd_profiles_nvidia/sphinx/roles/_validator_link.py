# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from typing import Any

from docutils import nodes
from sphinx.application import Sphinx

# Default validator configurations
DEFAULT_VALIDATORS = {
    "oav": {
        "url_template": "https://nvidia-omniverse.github.io/usd-validation-nvidia/validation/docs/requirements.html#{code}",
        "latest_version": "latest",
    },
}


def _get_validator(config: Any, validator_key: str) -> dict:
    """Get validator config, merging defaults with overrides."""
    overrides = config.validator_links
    validator = DEFAULT_VALIDATORS.get(validator_key, {}).copy()
    validator.update(overrides.get(validator_key, {}))
    return validator


def validator_link_role(
    name, rawtext, text, lineno, inliner, options={}, content=[]
) -> tuple[list[nodes.raw], list[nodes.raw]]:
    """
    Generic validator link role for specific versions.

    Example:

    .. code-block:: markdown
        {validator-link}`oav:1.0_aa-002`

    .. code-block:: rst
        :validator-link:`oav:1.0_aa-002`
    """
    config = inliner.document.settings.env.config

    try:
        validator_key, rest = text.split(":", 1)
    except ValueError:
        msg = inliner.reporter.error(f"Invalid format. Expected 'validator:version_code', got: {text}")
        return [], [msg]

    validator = _get_validator(config, validator_key)
    if not validator:
        msg = inliner.reporter.error(f"Unknown validator: {validator_key}")
        return [], [msg]

    try:
        raw_version, code = rest.split("_")
    except ValueError:
        msg = inliner.reporter.error(f"Invalid format. Expected 'version_code', got: {rest}")
        return [], [msg]

    version = raw_version.replace("+", "")

    url = validator["url_template"].format(version=version.strip(), code=code.strip())
    html = f'<a class="reference external" href="{url}"><span class="tag tag-nvidia">{raw_version}</span></a>'
    return [nodes.raw("", html, format="html")], []


def validator_latest_link_role(
    name, rawtext, text, lineno, inliner, options={}, content=[]
) -> tuple[list[nodes.raw], list[nodes.raw]]:
    """
    Generic validator link role for the latest version.

    Example:

    .. code-block:: markdown
        {validator-latest-link}`oav:aa-002`

    .. code-block:: rst
        :validator-latest-link:`oav:aa-002`
    """
    config = inliner.document.settings.env.config

    try:
        validator_key, code = text.split(":", 1)
    except ValueError:
        msg = inliner.reporter.error(f"Invalid format. Expected 'validator:code', got: {text}")
        return [], [msg]

    validator = _get_validator(config, validator_key)
    if not validator:
        msg = inliner.reporter.error(f"Unknown validator: {validator_key}")
        return [], [msg]

    version = validator.get("latest_version", "latest")
    url = validator["url_template"].format(version=version.strip(), code=code.strip())
    html = f'<a class="reference external" href="{url}"><span class="tag tag-nvidia">{version}+</span></a>'
    return [nodes.raw("", html, format="html")], []


def setup(app: Sphinx) -> dict[str, Any]:
    """
    Setup generic validator link roles.

    Args:
        app: The Sphinx application object.

    Returns:
        A dictionary containing the version of the extension.
    """
    app.add_config_value("validator_links", {}, "env")
    app.add_role("validator-link", validator_link_role)
    app.add_role("validator-latest-link", validator_latest_link_role)
    return {"version": "0.1"}
