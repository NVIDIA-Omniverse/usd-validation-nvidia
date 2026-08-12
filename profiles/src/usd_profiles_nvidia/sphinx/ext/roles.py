# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from typing import Any

from sphinx.application import Sphinx

from usd_profiles_nvidia.sphinx.roles import (
    compatibility_setup,
    manual_validation_setup,
    oav_validator_link_setup,
    tag_setup,
    validator_link_setup,
)


def setup(app: Sphinx) -> dict[str, Any]:
    """
    Setup all available roles. This includes:
    - tag: Tag role for the OpenUSD Profiles.
    - compatibility: Compatibility role for the OpenUSD Profiles.
    - manual-validation: Manual validation role for the OpenUSD Profiles.
    - oav-validator-link: USD Validation NVIDIA link role for profile specs.

    Args:
        app: The Sphinx application object.

    Returns:
        A dictionary containing the version of the extension.
    """
    tag_setup(app)
    compatibility_setup(app)
    manual_validation_setup(app)
    oav_validator_link_setup(app)
    validator_link_setup(app)
    return {
        "version": "0.1",
    }
