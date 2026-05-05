# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest
from importlib.metadata import PackageNotFoundError
from unittest.mock import patch

import nvidia_usd_validation._version as version_module
from nvidia_usd_validation import __version__, get_version


class TestVersion(unittest.TestCase):
    def test___version___is_string(self):
        self.assertIsInstance(__version__, str)
        self.assertRegex(__version__, r"^\d+\.\d+\.\d+.*$")

    def test_get_version_matches___version__(self):
        version = get_version()
        self.assertEqual(version, __version__)

    def test_get_version_falls_back_when_metadata_is_missing(self):
        with patch.object(version_module, "_metadata_version", side_effect=PackageNotFoundError):
            self.assertEqual(get_version(), "1.18.0")
