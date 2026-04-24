# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests",
# ]
# ///

# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""
Python wheel publishing script for KitMaker Portal API.
"""

import argparse
import logging
import os
import re
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


def get_version_from_wheel(wheel_name):
    """Extract version from wheel filename."""
    match = re.search(r"^nvidia_usd_validation-([^-]+)-", wheel_name)
    if match:
        version = match.group(1)
        return version

    return ""


def register_release_with_kitmaker(wheel_filename: str, version: str, dry_run: bool) -> bool:
    """
    Register a wheel release with the KitMaker Portal API for publication to PyPI.

    This script is only called for ready-to-release builds, so it always publishes
    to both DevZone and PyPI.

    Args:
        wheel_filename: Name of the wheel file
        version: Version string for the artifact path
        dry_run: Whether to dry run the script

    Returns:
        bool: True if registration succeeded, False otherwise
    """
    api_token = os.environ.get("KITMAKER_API_TOKEN")
    if not api_token:
        logger.error("KITMAKER_API_TOKEN environment variable not set")
        return False

    payload = {
        "project_name": "nvidia-usd-validation",
        "payload": [
            {
                "pic": "miguelh@nvidia.com",
                "job_type": "wheel-release-job",
                "publish_to": "both_devzone_pypi",
                "url": f"https://urm.nvidia.com/artifactory/ct-omniverse-pypi/nvidia-usd-validation/{version}/{wheel_filename}",
                "size": "small",
                "upload": not dry_run,
            }
        ],
    }
    try:
        logger.info("Registering release with KitMaker Portal: both_devzone_pypi")
        response = requests.post(
            "https://kitmaker-portal.nvidia.com/api/v0/projects/2014/releases",
            json=payload,
            headers={"Authorization": f"Bearer {api_token}"},
            verify=False,  # CI/CD runners may not have NVIDIA internal CA certificates installed
            timeout=60,
        )
        if response.status_code in (200, 201, 202):
            logger.info(f"Successfully registered release: {response.text}")
            return True
        else:
            logger.error(f"API request failed with status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Failed to call KitMaker Portal API: {e}")
        return False


def main():
    """Main function to publish wheel files via KitMaker Portal API."""
    parser = argparse.ArgumentParser(description="Publish wheel files to PyPI via KitMaker Portal")
    parser.add_argument(
        "--wheel-dir",
        help="Directory containing wheel files (relative to repo root)",
        required=True,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run the script",
        default=False,
    )

    args = parser.parse_args()
    logger.info(f"Wheel directory: {args.wheel_dir}")
    logger.info(f"Dry run: {args.dry_run}")

    wheel_count = 0
    logger.info("Starting wheel publishing...")

    # Find all wheel files in the specified directory
    packages_dir = Path(args.wheel_dir)

    if not packages_dir.exists():
        raise Exception(f"Directory does not exist: {packages_dir}")

    if not packages_dir.is_dir():
        raise Exception(f"Path is not a directory: {packages_dir}")

    wheel_files = list(packages_dir.glob("**/*.whl"))

    if not wheel_files:
        raise Exception(f"No wheel files found in {packages_dir}")

    for wheel_path in wheel_files:
        if wheel_path.is_file():
            wheel_filename = wheel_path.name
            logger.info(f"Processing wheel: {wheel_filename}")

            # Extract metadata from wheel filename
            version = get_version_from_wheel(wheel_filename)
            logger.info(f"  Version: {version}")

            # Register release with KitMaker Portal API
            if register_release_with_kitmaker(wheel_filename, version, args.dry_run):
                logger.info(f"Successfully registered release for {wheel_filename}")
                wheel_count += 1
            else:
                raise Exception(f"Failed to register release with KitMaker Portal for {wheel_filename}")
        else:
            logger.info(f"File does not exist or is not a regular file: {wheel_path}")

    if wheel_count == 0:
        raise Exception(f"No wheel files found in {packages_dir}")
    else:
        logger.info(f"Successfully registered {wheel_count} wheel(s) with KitMaker Portal")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    main()
