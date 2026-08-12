# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from usd_profiles_nvidia.model import Specifications
from usd_profiles_nvidia.parsers import SpecificationsParser
from usd_profiles_nvidia.store import RequirementStore


def parse_specifications(app) -> None:
    """
    Parse the requirements from the specifications and store them in the environment.
    """
    specifications: Specifications = SpecificationsParser(root_dir=app.srcdir).parse()
    app.env.specifications = specifications

    requirement_store: RequirementStore = RequirementStore(specifications.requirements)
    app.env.requirement_store = requirement_store


def setup(app) -> dict[str, bool]:
    """
    Setup the Sphinx extension to build specifications.
    """
    app.connect("builder-inited", parse_specifications)
    return {
        "version": "1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
