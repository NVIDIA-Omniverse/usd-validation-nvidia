# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest

from nvidia_usd_validation import __version__


class TestVersion(unittest.TestCase):
    def test_version_is_set(self):
        self.assertTrue(__version__)
