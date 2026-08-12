# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from __future__ import annotations

import argparse
import logging
import sys

from usd_profiles_nvidia.lock import ProfilesLockError, ProfilesLockManager
from usd_profiles_nvidia.parsers import SpecificationsParser

logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check or update a profiles.lock file.")
    parser.add_argument(
        "-f",
        "--docs-root",
        required=True,
        help="Root directory containing capabilities/, features/, and profiles/ subdirectories.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check the current specifications against the lock file. This is the default action.",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Write the current feature source fingerprints to the lock file.",
    )
    args = parser.parse_args()

    if args.check and args.update:
        parser.error("--check and --update are mutually exclusive")

    manager = ProfilesLockManager.resolve(args.docs_root)

    try:
        specifications = SpecificationsParser(root_dir=args.docs_root).parse()
        if args.update:
            manager.update(specifications.features)
            print(f"Wrote profiles lock: {manager.lock_file.path}")
        else:
            result = manager.check(specifications.features)
            if result.skipped:
                print(f"No profiles lock found at {manager.lock_file.path}; skipping.")
            else:
                print(f"Profiles lock is up to date: {manager.lock_file.path} ({result.checked} features)")
        return 0
    except ProfilesLockError as e:
        logger.error(e)
        return 1
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
