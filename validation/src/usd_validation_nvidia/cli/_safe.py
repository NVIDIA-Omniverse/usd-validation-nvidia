# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import sys

from .._dependencies import is_usd_available, is_usd_distribution_conflict
from ._minimal import minimal_cli_main

__all__ = [
    "cli_main",
]


def cli_main(args: list[str] | None = None) -> None:
    """Run the validation CLI through a USD-safe entry point.

    Args:
        args: Optional CLI arguments. When ``None``, argparse reads from ``sys.argv``.
    """
    if is_usd_distribution_conflict():
        print(
            "Error: Conflicting USD Python distributions detected: "
            "usd-core and usd-exchange are both installed. "
            "Install only one USD provider: usd-validation-nvidia[usd] or usd-validation-nvidia[usdex].",
            file=sys.stderr,
        )
        sys.exit(1)

    if not is_usd_available():
        exit_code = minimal_cli_main(args)
        if exit_code:
            sys.exit(exit_code)
        return

    from .._plugins import PluginManager
    from ._validation import cli_main as real_cli_main

    with PluginManager():
        real_cli_main(args)
