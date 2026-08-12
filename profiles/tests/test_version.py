# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import unittest
from pathlib import Path

from usd_profiles_nvidia import __version__, get_version
from usd_profiles_nvidia.model import IdVersion, Version


class TestPackageVersion(unittest.TestCase):
    VERSION_PATH = Path(__file__).resolve().parents[2] / "VERSION.md"

    def test_get_version_ok(self):
        self.assertEqual(get_version(), __version__)

    def test__version__ok(self):
        expected_version = self.VERSION_PATH.read_text(encoding="utf-8").strip()

        self.assertEqual(__version__, expected_version)


class TestVersion(unittest.TestCase):
    def test_init_str(self):
        version = Version("1.2.3")

        self.assertEqual(version.major, 1)
        self.assertEqual(version.minor, 2)
        self.assertEqual(version.patch, 3)

    def test_init_int(self):
        version = Version(1, 2, 3)

        self.assertEqual(version.major, 1)
        self.assertEqual(version.minor, 2)
        self.assertEqual(version.patch, 3)

    def test_str(self):
        version = Version("1.2.3")

        self.assertEqual(str(version), "1.2.3")

    def test_repr(self):
        version = Version("1.2.3")

        self.assertEqual(repr(version), "Version(major=1, minor=2, patch=3)")

    def test_eq(self):
        version = Version("1.2.3")
        other = Version(1, 2, 3)

        self.assertEqual(version, other)

    def test_hash(self):
        version = Version("1.2.3")

        self.assertEqual(hash(version), hash((1, 2, 3)))

    def test_lt(self):
        version = Version("1.2.3")
        other = Version("1.2.4")

        self.assertTrue(version < other)

    def test_le(self):
        version = Version("1.2.3")
        other = Version("1.2.4")

        self.assertTrue(version <= other)

    def test_init_str_integer_only(self):
        """Version('1') is treated as 1.0.0 internally but str() returns '1'."""
        version = Version("1")
        self.assertEqual(version.major, 1)
        self.assertEqual(version.minor, 0)
        self.assertEqual(version.patch, 0)

    def test_str_integer_only(self):
        """str(Version('1')) returns '1', not '1.0.0'."""
        self.assertEqual(str(Version("1")), "1")

    def test_str_integer_only_multidigit(self):
        self.assertEqual(str(Version("12")), "12")

    def test_eq_integer_only_and_semver(self):
        """Version('1') and Version(1,0,0) are equal despite different str representations."""
        self.assertEqual(Version("1"), Version(1, 0, 0))

    def test_hash_integer_only_matches_semver(self):
        """Hash is the same since integer_only is excluded from hash."""
        self.assertEqual(hash(Version("1")), hash(Version(1, 0, 0)))

    def test_init_str_underscore(self):
        """Version('23_05') → major=23, minor=5, patch=0, str() → '23_05'."""
        version = Version("23_05")
        self.assertEqual(version.major, 23)
        self.assertEqual(version.minor, 5)
        self.assertEqual(version.patch, 0)
        self.assertEqual(str(version), "23_05")

    def test_init_str_two_parts_raises(self):
        """Version('1.2') is still invalid — must be 1-part or 3-part"""
        with self.assertRaises(ValueError):
            Version("1.2")


class TestIdVersion(unittest.TestCase):
    def test_parse_at_separator(self):
        id_version = IdVersion.parse("VG.001@1.0.0")
        self.assertEqual(id_version.id, "VG.001")
        self.assertEqual(id_version.version, Version("1.0.0"))

    def test_parse_no_version(self):
        id_version = IdVersion.parse("VG.001")
        self.assertEqual(id_version.id, "VG.001")
        self.assertIsNone(id_version.version)

    def test_parse_dot_v_suffix(self):
        """com.nvidia.usd.geometry.v1 -> id='com.nvidia.usd.geometry', version=Version(1,0,0)"""
        id_version = IdVersion.parse("com.nvidia.usd.geometry.v1")
        self.assertEqual(id_version.id, "com.nvidia.usd.geometry")
        self.assertEqual(id_version.version, Version("1"))

    def test_parse_dot_v_suffix_multidigit(self):
        id_version = IdVersion.parse("com.nvidia.simready.materials.v12")
        self.assertEqual(id_version.id, "com.nvidia.simready.materials")
        self.assertEqual(id_version.version, Version(12, 0, 0))

    def test_parse_dot_v_underscore_format(self):
        """USD Profiles proposal format: usd.core.v23_05"""
        id_version = IdVersion.parse("usd.core.v23_05")
        self.assertEqual(id_version.id, "usd.core")
        self.assertEqual(id_version.version, Version("23_05"))

    def test_parse_dot_v_suffix_no_at(self):
        """Simple .vN suffix without @ separator."""
        id_version = IdVersion.parse("some.id.v2")
        self.assertEqual(id_version.id, "some.id")
        self.assertEqual(id_version.version, Version(2, 0, 0))
