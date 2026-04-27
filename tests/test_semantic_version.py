# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest
from unittest.mock import Mock

from nvidia_usd_validation import SemVer


class SemVerTest(unittest.TestCase):
    def setUp(self):
        self.mock_capability = Mock(spec=SemVer)
        self.mock_capability.id = "test_semver"
        self.mock_capability.version = "1.0.0"
        self.mock_capability.name = "test_semver"

    def test_semver_creation_from_default(self):
        """Test creating SemVer from default."""
        semver = SemVer()
        self.assertEqual(semver.major, 0)
        self.assertEqual(semver.minor, 1)
        self.assertEqual(semver.patch, 0)
        self.assertIsNone(semver.prerelease)
        self.assertIsNone(semver.build)

    def test_semver_creation_from_none(self):
        """Test creating SemVer from None."""
        semver = SemVer(None)
        self.assertEqual(semver.major, 0)
        self.assertEqual(semver.minor, 1)
        self.assertEqual(semver.patch, 0)
        self.assertIsNone(semver.prerelease)
        self.assertIsNone(semver.build)

    def test_semver_creation_from_int(self):
        """Test creating SemVer from int."""
        semver = SemVer(1)
        self.assertEqual(semver.major, 1)
        self.assertEqual(semver.minor, 0)
        self.assertEqual(semver.patch, 0)
        self.assertIsNone(semver.prerelease)
        self.assertIsNone(semver.build)

    def test_semver_creation_from_string(self):
        """Test creating SemVer from string."""
        semver = SemVer("1.2.3")
        self.assertEqual(semver.major, 1)
        self.assertEqual(semver.minor, 2)
        self.assertEqual(semver.patch, 3)
        self.assertIsNone(semver.prerelease)
        self.assertIsNone(semver.build)

    def test_semver_creation_from_components(self):
        """Test creating SemVer from individual components."""
        semver = SemVer(1, 2, 3, "alpha.1", "build.1")
        self.assertEqual(semver.major, 1)
        self.assertEqual(semver.minor, 2)
        self.assertEqual(semver.patch, 3)
        self.assertEqual(semver.prerelease, "alpha.1")
        self.assertEqual(semver.build, "build.1")

    def test_semver_comparison(self):
        """Test SemVer comparison operations."""
        v1 = SemVer("1.0.0")
        v2 = SemVer("2.0.0")
        v1_1 = SemVer("1.1.0")
        v1_0_1 = SemVer("1.0.1")

        # Test less than
        self.assertTrue(v1 < v2)
        self.assertTrue(v1 < v1_1)
        self.assertTrue(v1 < v1_0_1)

        # Test equal
        self.assertEqual(v1, SemVer("1.0.0"))
        self.assertNotEqual(v1, v2)

    def test_semver_with_prerelease(self):
        """Test SemVer with prerelease versions."""
        v1 = SemVer("1.0.0")
        v1_alpha = SemVer("1.0.0-alpha.1")
        v1_beta = SemVer("1.0.0-beta.1")

        # Prerelease versions are less than release versions
        self.assertTrue(v1_alpha < v1)
        self.assertTrue(v1_beta < v1)
        self.assertTrue(v1_alpha < v1_beta)  # alpha < beta

    def test_semver_equality_with_build(self):
        """Test SemVer equality includes build metadata."""
        v1 = SemVer("1.0.0+build.1")
        v2 = SemVer("1.0.0+build.2")
        v3 = SemVer("1.0.0")

        # Build metadata should be included in equality
        self.assertNotEqual(v1, v2)
        self.assertNotEqual(v1, v3)

    def test_semver_is_compatible(self):
        """Test SemVer compatibility checking."""
        v1 = SemVer("1.0.0")
        v1_1 = SemVer("1.1.0")
        v2 = SemVer("2.0.0")

        # Same major version should be compatible
        self.assertTrue(v1_1.is_compatible(v1))
        self.assertTrue(v1.is_compatible(v1))

        # Different major version should not be compatible
        self.assertFalse(v2.is_compatible(v1))

    def test_semver_repr(self):
        """Test SemVer string representation."""
        v1 = SemVer("1.2.3")
        v2 = SemVer("1.2.3-alpha.1")
        v3 = SemVer("1.2.3+build.1")
        v4 = SemVer("1.2.3-alpha.1+build.1")

        self.assertEqual(str(v1), "1.2.3")
        self.assertEqual(str(v2), "1.2.3-alpha.1")
        self.assertEqual(str(v3), "1.2.3+build.1")
        self.assertEqual(str(v4), "1.2.3-alpha.1+build.1")

    def test_semver_invalid_format(self):
        """Test SemVer with invalid format raises ValueError."""
        with self.assertRaises(ValueError):
            SemVer("invalid")

        with self.assertRaises(ValueError):
            SemVer("1.2")

        with self.assertRaises(ValueError):
            SemVer("1.2.3.4.5")

    def test_semver_latest_constant(self):
        """Test SemVer.LATEST constant."""
        self.assertEqual(SemVer.LATEST, "latest")

    def test_semver_hash(self):
        """Test SemVer hash."""
        v1 = SemVer("1.2.3")
        v2 = SemVer("1.2.3")
        self.assertEqual(hash(v1), hash(v2))
