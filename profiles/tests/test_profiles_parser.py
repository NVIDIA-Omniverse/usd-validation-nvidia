# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import unittest
from pathlib import Path

from usd_profiles_nvidia.markdown import ProfilesParser
from usd_profiles_nvidia.model import IdVersion, ProfileFeature, Version


class TestProfilesParser(unittest.TestCase):

    def test_parse_ok(self):
        root_dir = Path(__file__).parent / "resources" / "simple-profile"
        parser = ProfilesParser(root_dir=str(root_dir), path=str(root_dir))
        profiles = parser.parse()

        self.assertGreaterEqual(len(profiles), 1)
        self.assertEqual(profiles[0].id, "name")
        self.assertEqual(profiles[0].version, "1.0.0")
        self.assertEqual(profiles[0].display_name, "Name")
        self.assertEqual(profiles[0].message, "Description")
        self.assertEqual(len(profiles[0].features), 2)
        self.assertEqual(profiles[0].features[0], ProfileFeature(IdVersion("simple", Version(1, 0, 0))))
        self.assertEqual(profiles[0].features[1], ProfileFeature(IdVersion("complex", Version(1, 0, 0))))

    def test_does_not_parse_toml(self):
        root_dir = Path(__file__).parent / "resources" / "toml-profiles"
        parser = ProfilesParser(root_dir=str(root_dir), path=str(root_dir))

        self.assertEqual(parser.parse(), [])
