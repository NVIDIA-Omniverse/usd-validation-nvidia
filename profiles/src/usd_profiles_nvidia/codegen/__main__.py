# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Command-line interface for code generation.

Usage:
    python -m usd_profiles_nvidia.codegen --docs-root docs/ --destination-dir python/ --package-name omni.profiles
    python -m usd_profiles_nvidia.codegen --docs-root docs/ --destination-dir python/ --package-name com.nvidia.simready --reverse-domain com.nvidia.simready
"""

from __future__ import annotations

import argparse
import logging
import sys

from usd_profiles_nvidia.codegen._cli import add_arguments, generate

logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Python from Profiles Markdown files.")
    add_arguments(parser)
    args = parser.parse_args()
    try:
        package_name: str = args.package_name or args.namespace or ""
        reverse_domain: str = args.reverse_domain or ""
        generate(args.docs_root, args.destination_dir, package_name, reverse_domain)
        return 0
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
