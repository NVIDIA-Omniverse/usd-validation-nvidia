# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import tempfile
import unittest
from pathlib import Path
from shutil import copytree

from usd_profiles_nvidia.model import IdVersion, ProfileFeature, Version
from usd_profiles_nvidia.parsers import ProfilesParser
from usd_profiles_nvidia.toml import TomlProfilesParser


class TestTomlProfilesParser(unittest.TestCase):

    def setUp(self):
        self.root_dir = str(Path(__file__).parent / "resources" / "toml-profiles")
        self.profiles = TomlProfilesParser(root_dir=self.root_dir, path=self.root_dir).parse()

    def test_parse_profiles(self):
        profile_ids = [(p.id, str(p.version)) for p in self.profiles]
        self.assertIn(("Prop-Robotics-Neutral", "1.0.0"), profile_ids)
        self.assertIn(("Prop-Robotics-Neutral", "2.0.0"), profile_ids)
        self.assertIn(("Robot-Body-Isaac", "1.0.0"), profile_ids)
        self.assertEqual(len(self.profiles), 3)

    def test_parse_profile_features(self):
        neutral_v1 = next(p for p in self.profiles if p.id == "Prop-Robotics-Neutral" and str(p.version) == "1.0.0")
        self.assertEqual(len(neutral_v1.features), 2)
        self.assertEqual(neutral_v1.features[0], ProfileFeature(IdVersion("FET001_BASE_NEUTRAL", Version("0.1.0"))))
        self.assertEqual(neutral_v1.features[1], ProfileFeature(IdVersion("FET003_BASE_NEUTRAL", Version("0.1.0"))))
        self.assertFalse(neutral_v1.features[0].optional)
        self.assertFalse(neutral_v1.features[1].optional)

    def test_parse_optional_profile_feature(self):
        root_dir = str(Path(__file__).parent / "resources" / "optional-profile-spec" / "profiles")
        profiles = TomlProfilesParser(root_dir=root_dir, path=root_dir).parse()

        profile = next(p for p in profiles if p.id == "Optional-Profile")
        self.assertEqual(
            profile.features,
            [
                ProfileFeature(IdVersion("required", Version("1.0.0"))),
                ProfileFeature(IdVersion("extra", Version("1.0.0")), optional=True),
            ],
        )

    def test_parse_multi_version_profile(self):
        neutral_v1 = next(p for p in self.profiles if p.id == "Prop-Robotics-Neutral" and str(p.version) == "1.0.0")
        neutral_v2 = next(p for p in self.profiles if p.id == "Prop-Robotics-Neutral" and str(p.version) == "2.0.0")
        self.assertEqual(neutral_v1.features[0].feature, IdVersion("FET001_BASE_NEUTRAL", Version("0.1.0")))
        self.assertEqual(neutral_v2.features[0].feature, IdVersion("FET001_BASE_NEUTRAL", Version("1.0.0")))

    def test_parse_robot_body_isaac(self):
        isaac = next(p for p in self.profiles if p.id == "Robot-Body-Isaac")
        self.assertEqual(isaac.version, "1.0.0")
        self.assertEqual(len(isaac.features), 3)
        self.assertEqual(isaac.features[1].feature, IdVersion("FET004_ROBOT_PHYSX", Version("0.2.0")))

    def test_parse_without_toml_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertEqual(TomlProfilesParser(root_dir=tmpdir, path=tmpdir).parse(), [])

    def test_profile_name_preserved(self):
        isaac = next(p for p in self.profiles if p.id == "Robot-Body-Isaac")
        self.assertEqual(isaac.display_name, "Robot-Body-Isaac")

    def test_malformed_version_not_a_table(self):
        # Version entry is a plain string instead of a TOML inline table — hits
        # the per-version isinstance(version_data, dict) check.
        with tempfile.TemporaryDirectory() as tmpdir:
            toml_path = str(Path(tmpdir) / "profiles.toml")
            Path(toml_path).write_text('[Bad]\n"1.0.0" = "just a string"\n')
            with self.assertRaises(ValueError) as ctx:
                TomlProfilesParser(root_dir=tmpdir, path=tmpdir).parse()
            self.assertIn("must be a table", str(ctx.exception))

    def test_malformed_missing_features_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            toml_path = str(Path(tmpdir) / "profiles.toml")
            Path(toml_path).write_text('[Bad]\n"1.0.0" = {other = "data"}\n')
            with self.assertRaises(ValueError) as ctx:
                TomlProfilesParser(root_dir=tmpdir, path=tmpdir).parse()
            self.assertIn("missing required 'features' key", str(ctx.exception))

    def test_malformed_feature_missing_version(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            toml_path = str(Path(tmpdir) / "profiles.toml")
            Path(toml_path).write_text('[Bad]\n"1.0.0" = {features = [{FET001 = {}}]}\n')
            with self.assertRaises(KeyError):
                TomlProfilesParser(root_dir=tmpdir, path=tmpdir).parse()

    def test_malformed_feature_multiple_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            toml_path = str(Path(tmpdir) / "profiles.toml")
            Path(toml_path).write_text(
                "[Bad]\n"
                '"1.0.0" = {features = ['
                '{FET001 = {version = "1.0.0"}, FET002 = {version = "1.0.0"}, optional = true}'
                "]}\n"
            )
            with self.assertRaises(ValueError) as ctx:
                TomlProfilesParser(root_dir=tmpdir, path=tmpdir).parse()
            self.assertIn("Expected exactly one feature key per entry", str(ctx.exception))

    def test_malformed_feature_missing_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            toml_path = str(Path(tmpdir) / "profiles.toml")
            Path(toml_path).write_text('[Bad]\n"1.0.0" = {features = [{optional = true}]}\n')
            with self.assertRaises(ValueError) as ctx:
                TomlProfilesParser(root_dir=tmpdir, path=tmpdir).parse()
            self.assertIn("Expected exactly one feature key per entry", str(ctx.exception))

    def test_malformed_bad_version_string(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            toml_path = str(Path(tmpdir) / "profiles.toml")
            Path(toml_path).write_text('[Bad]\n"not.a.ver.sion" = {features = []}\n')
            with self.assertRaises(ValueError):
                TomlProfilesParser(root_dir=tmpdir, path=tmpdir).parse()

    def test_empty_features_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            toml_path = str(Path(tmpdir) / "profiles.toml")
            Path(toml_path).write_text('[EmptyProfile]\n"1.0.0" = {features = []}\n')
            profiles = TomlProfilesParser(root_dir=tmpdir, path=tmpdir).parse()
            self.assertEqual(len(profiles), 1)
            self.assertEqual(profiles[0].id, "EmptyProfile")
            self.assertEqual(profiles[0].features, [])


class TestProfilesParserTomlFallback(unittest.TestCase):
    """The agnostic ProfilesParser should aggregate Markdown and TOML profiles."""

    def test_profiles_parser_finds_toml(self):
        root_dir = str(Path(__file__).parent / "resources" / "toml-profiles")
        parser = ProfilesParser(root_dir=root_dir, path=root_dir)
        profiles = parser.parse()

        self.assertEqual(len(profiles), 3)
        profile_ids = {p.id for p in profiles}
        self.assertIn("Prop-Robotics-Neutral", profile_ids)
        self.assertIn("Robot-Body-Isaac", profile_ids)

    def test_profiles_parser_falls_back_to_markdown(self):
        root_dir = str(Path(__file__).parent / "resources" / "simple-profile")
        parser = ProfilesParser(root_dir=root_dir, path=root_dir)
        profiles = parser.parse()

        self.assertGreaterEqual(len(profiles), 1)
        self.assertEqual(profiles[0].id, "name")

    def test_profiles_parser_combines_markdown_and_toml(self):
        source_dir = Path(__file__).parent / "resources" / "simple-profile"
        with tempfile.TemporaryDirectory() as tmpdir:
            root_dir = Path(tmpdir)
            copytree(source_dir, root_dir, dirs_exist_ok=True)
            (root_dir / "profiles.toml").write_text('[Toml-Only]\n"1.0.0" = {features = []}\n')

            parser = ProfilesParser(root_dir=str(root_dir), path=str(root_dir))
            profiles = parser.parse()

        profile_ids = {profile.id for profile in profiles}
        self.assertIn("name", profile_ids)
        self.assertIn("Toml-Only", profile_ids)
