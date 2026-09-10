# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import argparse
import sys

from .._version import __version__

__all__ = [
    "create_minimal_validation_parser",
    "minimal_cli_main",
]


def create_minimal_validation_parser() -> argparse.ArgumentParser:
    """Create the no-USD parser that recognizes version queries only."""
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--version", action="store_true")
    return parser


def minimal_cli_main(args: list[str] | None = None) -> int:
    """Run the no-USD CLI surface and return a process exit code.

    Args:
        args: Optional CLI arguments. When ``None``, argparse reads from ``sys.argv``.

    Returns:
        The process exit code for the minimal CLI surface.
    """
    parser = create_minimal_validation_parser()
    namespace, _ = parser.parse_known_args(args)

    if namespace.version:
        print(__version__)
        return 0

    print(
        "Warning: No USD installation detected. "
        "Install usd-validation-nvidia[usdex] for the USD Exchange stack "
        "or usd-validation-nvidia[usd] for the PyPI usd-core stack.",
        file=sys.stderr,
    )
    return 1
