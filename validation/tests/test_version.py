# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest
from pathlib import Path

from usd_validation_nvidia import __version__, get_version


class TestVersion(unittest.TestCase):
    VERSION_PATH = Path(__file__).resolve().parents[2] / "VERSION.md"

    def test_get_version_ok(self):
        self.assertEqual(get_version(), __version__)

    def test__version__ok(self):
        expected_version = self.VERSION_PATH.read_text(encoding="utf-8").strip()

        self.assertEqual(__version__, expected_version)
