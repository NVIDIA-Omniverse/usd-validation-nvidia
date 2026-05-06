# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from ._cli import cli_main
from ._plugins import PluginManager


def main():
    with PluginManager():
        cli_main()


if __name__ == "__main__":
    main()
