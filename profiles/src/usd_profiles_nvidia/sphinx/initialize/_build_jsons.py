# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import json
import logging
import os

from usd_profiles_nvidia.api import Capability, Feature
from usd_profiles_nvidia.json import JsonSerialize
from usd_profiles_nvidia.model import Profile, Specifications

logger = logging.getLogger(__name__)


def _serialize(obj: Capability | Feature | Profile, destination_file: str):
    with open(destination_file, "w", encoding="utf-8") as destination_fptr:
        destination_fptr.write(json.dumps(obj, cls=JsonSerialize, indent=4))


def process_and_generate_jsons(app) -> None:
    """
    Process requirement files and generate JSON files during initialization.
    Finds all requirement files, extracts requirements, and generates JSON files.
    """
    config_output_dir = os.path.join(app.outdir, "config")
    os.makedirs(config_output_dir, exist_ok=True)

    specifications: Specifications = app.env.specifications

    for capability in specifications.capabilities:
        output_file = os.path.join(config_output_dir, f"{capability.id}.json")
        logger.info(f"Generated json file for {capability.id} at {output_file}")
        _serialize(capability, output_file)

    for feature in specifications.features:
        output_file = os.path.join(config_output_dir, f"{feature.id}.json")
        logger.info(f"Generated json file for {feature.id} at {output_file}")
        _serialize(feature, output_file)

    for profile in specifications.profiles:
        output_file = os.path.join(config_output_dir, f"{profile.id}.json")
        logger.info(f"Generated json file for {profile.id} at {output_file}")
        _serialize(profile, output_file)


def setup(app) -> dict[str, bool]:
    """
    Setup the Sphinx extension to generate JSON files.
    Connects to the builder-inited event to process requirements early.
    """
    app.connect("builder-inited", process_and_generate_jsons)
    return {
        "version": "1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
