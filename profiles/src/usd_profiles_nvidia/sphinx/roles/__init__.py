# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from ._compatibility import setup as compatibility_setup
from ._manual_validation import setup as manual_validation_setup
from ._oav_validator_link import setup as oav_validator_link_setup
from ._tags import setup as tag_setup
from ._validator_link import setup as validator_link_setup

__all__ = [
    "compatibility_setup",
    "manual_validation_setup",
    "oav_validator_link_setup",
    "tag_setup",
    "validator_link_setup",
]
