# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from __future__ import annotations

from argparse import ArgumentParser


def add_arguments(parser: ArgumentParser, required: bool = True) -> None:
    """Add codegen arguments to an argument parser."""
    parser.add_argument(
        "-f",
        "--docs-root",
        dest="docs_root",
        required=required,
        help="Where to find profiles markdown files, i.e. docs/.",
    )
    parser.add_argument(
        "-d",
        "--destination-dir",
        dest="destination_dir",
        required=required,
        help="Destination dir for the generated code, i.e. python/.",
    )
    parser.add_argument(
        "-p",
        "--package-name",
        dest="package_name",
        required=False,
        help="Python package path for generated modules, e.g. omni.profiles.",
    )
    parser.add_argument(
        "-r",
        "--reverse-domain",
        dest="reverse_domain",
        required=False,
        default="",
        help=("Reverse-domain prefix for spec identifiers, e.g. com.nvidia.simready. Empty means legacy behavior."),
    )
    # Deprecated: use --package-name and --reverse-domain instead.
    parser.add_argument(
        "-n",
        "--namespace",
        dest="namespace",
        required=False,
        help="Deprecated: use --package-name and --reverse-domain instead.",
    )


def generate(docs_root: str, destination_dir: str, package_name: str, reverse_domain: str = "") -> None:
    """Generate Python code from Profiles Markdown files."""
    from usd_profiles_nvidia.codegen._py_generate import PythonGenerator

    generator = PythonGenerator(
        docs_root=docs_root,
        destination_dir=destination_dir,
        package_name=package_name,
        reverse_domain=reverse_domain,
    )
    generator.generate()
