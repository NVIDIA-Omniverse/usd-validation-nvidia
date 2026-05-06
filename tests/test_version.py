# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest

from usd_validation_nvidia import __version__, get_version


class TestVersion(unittest.TestCase):
    def test___version___is_string(self):
        self.assertIsInstance(__version__, str)
        self.assertRegex(__version__, r"^\d+\.\d+\.\d+.*$")

    def test_get_version_matches___version__(self):
        version = get_version()
        self.assertEqual(version, __version__)
