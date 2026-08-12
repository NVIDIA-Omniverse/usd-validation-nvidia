# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import unittest

from usd_profiles_nvidia.model import Tag, tag_priority


class TestTag(unittest.TestCase):
    def test_tag_priority_uses_highest_priority_tag(self):
        self.assertEqual(
            tag_priority((Tag.PERFORMANCE.display_name, Tag.ESSENTIAL.display_name)),
            Tag.ESSENTIAL.priority,
        )

    def test_tag_priority_defaults_to_zero(self):
        self.assertEqual(tag_priority(()), 0)
