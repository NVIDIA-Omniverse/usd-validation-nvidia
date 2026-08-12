# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import hashlib
import os
import unittest
from shutil import copyfile
from tempfile import TemporaryDirectory

from usd_profiles_nvidia.api import Feature, RequirementRef
from usd_profiles_nvidia.lock import (
    ProfilesLockBuilder,
    ProfilesLockError,
    ProfilesLockFile,
    ProfilesLockManager,
)

LOCKS_ROOT = os.path.join(os.path.dirname(__file__), "resources", "locks")
PROFILES_LOCK = os.path.join(LOCKS_ROOT, "profiles.lock")


class TestProfilesLock(unittest.TestCase):
    def test_build_lock_hashes_sorted_feature_inputs(self):
        feature = Feature(
            id="FET003_BASE_NEUTRAL",
            version="0.1.0",
            path="features/FET_003_base_neutral",
            requirements=[
                RequirementRef("REQ002", "1.0.0"),
                RequirementRef("REQ001", "1.0.0"),
            ],
        )

        lock = ProfilesLockBuilder().build([feature])
        entry = lock.features["FET003_BASE_NEUTRAL@0.1.0"]

        payload = b'["REQ001@1.0.0","REQ002@1.0.0"]'
        self.assertEqual(entry.source.path, "features/FET_003_base_neutral")
        self.assertEqual(entry.source.hash, f"sha256:{hashlib.sha256(payload).hexdigest()}")

    def test_build_lock_allows_unversioned_feature_key(self):
        feature = Feature(
            id="FET003_BASE_NEUTRAL",
            version="",
            path="features/FET_003_base_neutral",
            requirements=[RequirementRef("REQ001", "1.0.0")],
        )

        lock = ProfilesLockBuilder().build([feature])

        self.assertIn("FET003_BASE_NEUTRAL", lock.features)

    def test_read_lock_fixture(self):
        loaded = ProfilesLockFile(PROFILES_LOCK).read()
        entry = loaded.features["FET003_BASE_NEUTRAL@0.1.0"]

        self.assertEqual(loaded.version, 1)
        self.assertEqual(entry.source.path, "features/FET_003_base_neutral")
        self.assertEqual(
            entry.source.hash,
            "sha256:b725b56145eb58f7c00c259a3070e4246a48ddbea7119c727707b62dfa5d7cb1",
        )

    def test_check_lock_skips_missing_optional_lock(self):
        feature = Feature(
            id="FET003_BASE_NEUTRAL",
            version="0.1.0",
            path="features/FET_003_base_neutral",
            requirements=[RequirementRef("REQ001", "1.0.0")],
        )

        with TemporaryDirectory() as tmpdirname:
            lock_file = os.path.join(tmpdirname, "profiles.lock")

            result = ProfilesLockManager(ProfilesLockFile(lock_file)).check([feature])

        self.assertTrue(result.skipped)
        self.assertEqual(result.checked, 0)

    def test_check_lock_accepts_matching_existing_feature(self):
        feature = Feature(
            id="FET003_BASE_NEUTRAL",
            version="0.1.0",
            path="features/FET_003_base_neutral",
            requirements=[RequirementRef("REQ001", "1.0.0")],
        )

        result = ProfilesLockManager(ProfilesLockFile(PROFILES_LOCK)).check([feature])

        self.assertFalse(result.skipped)
        self.assertEqual(result.checked, 1)

    def test_check_lock_detects_existing_feature_requirement_change(self):
        changed = Feature(
            id="FET003_BASE_NEUTRAL",
            version="0.1.0",
            path="features/FET_003_base_neutral",
            requirements=[RequirementRef("REQ002", "1.0.0")],
        )

        with self.assertRaisesRegex(ProfilesLockError, "changed its locked source fingerprint"):
            ProfilesLockManager(ProfilesLockFile(PROFILES_LOCK)).check([changed])

    def test_update_lock_refuses_existing_feature_requirement_change(self):
        changed = Feature(
            id="FET003_BASE_NEUTRAL",
            version="0.1.0",
            path="features/FET_003_base_neutral",
            requirements=[RequirementRef("REQ002", "1.0.0")],
        )
        bumped = Feature(
            id="FET003_BASE_NEUTRAL",
            version="0.2.0",
            path="features/FET_003_base_neutral",
            requirements=[RequirementRef("REQ002", "1.0.0")],
        )

        with TemporaryDirectory() as tmpdirname:
            lock_file = os.path.join(tmpdirname, "profiles.lock")
            copyfile(PROFILES_LOCK, lock_file)
            file = ProfilesLockFile(lock_file)
            manager = ProfilesLockManager(file)

            with self.assertRaisesRegex(ProfilesLockError, "source hash changed"):
                manager.update([changed])

            manager.update([bumped])

            loaded = file.read()
            self.assertEqual(set(loaded.features), {"FET003_BASE_NEUTRAL@0.2.0"})


if __name__ == "__main__":
    unittest.main()
