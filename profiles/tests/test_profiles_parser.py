# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import unittest
from pathlib import Path

from usd_profiles_nvidia.api import Feature, Profile, ProfileFeature
from usd_profiles_nvidia.markdown import ProfilesParser


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
        self.assertEqual(profiles[0].path, "profile-simple")
        self.assertIsInstance(profiles[0], Profile)
        self.assertEqual(len(profiles[0].features), 2)
        self.assertTrue(all(isinstance(feature, Feature) for feature in profiles[0].features))
        self.assertEqual(profiles[0].profile_features, [ProfileFeature(feature) for feature in profiles[0].features])

    def test_parse_single_markdown_file(self):
        root_dir = Path(__file__).parent / "resources" / "simple-profile"
        profile_path = root_dir / "profile-simple.md"

        profiles = ProfilesParser(root_dir=str(root_dir), path=str(profile_path)).parse()

        self.assertEqual([profile.id for profile in profiles], ["name"])

    def test_does_not_parse_toml(self):
        root_dir = Path(__file__).parent / "resources" / "toml-profiles"
        parser = ProfilesParser(root_dir=str(root_dir), path=str(root_dir))

        self.assertEqual(parser.parse(), [])
