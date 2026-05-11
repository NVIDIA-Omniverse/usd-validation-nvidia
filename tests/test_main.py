# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest
from unittest import mock

import usd_validation_nvidia.__main__ as main_module


class MainTest(unittest.TestCase):
    def test_main_runs_cli_inside_plugin_manager(self):
        calls = []

        class _PluginManager:
            def __enter__(self):
                calls.append("enter")

            def __exit__(self, exc_type, exc_value, traceback):
                calls.append("exit")

        with (
            mock.patch.object(main_module, "PluginManager", return_value=_PluginManager()),
            mock.patch.object(main_module, "cli_main", side_effect=lambda: calls.append("cli")),
        ):
            main_module.main()

        self.assertEqual(calls, ["enter", "cli", "exit"])
