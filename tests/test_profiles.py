# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest
from unittest.mock import Mock

from usd_validation_nvidia import (
    BaseRuleChecker,
    FeatureRegistry,
    Profile,
    ProfileRegistry,
    RequirementsRegistry,
    add_registry_profile_callback,
    register_feature,
    register_profile,
    register_profiles,
    register_requirements,
    unregister_feature,
    unregister_profile,
    unregister_profiles,
    unregister_requirements,
)
from usd_validation_nvidia.capabilities import Feature as FeatureDTO
from usd_validation_nvidia.capabilities import Profile as ProfileDTO
from usd_validation_nvidia.capabilities import Requirement as RequirementDTO


class TestProfileRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = ProfileRegistry()
        self.mock_profile = Mock(spec=Profile)
        self.mock_profile.id = "test_profile"
        self.mock_profile.version = "1.0.0"
        self.mock_profile.path = "/path/v1"
        self.mock_profile.capabilities = []

    def tearDown(self):
        try:
            unregister_profile(self.mock_profile)
        except ValueError:
            pass

    def test_add_profile(self):
        self.registry.add_profile(self.mock_profile)

        self.assertIn(self.mock_profile, self.registry.profiles)
        self.assertEqual(self.registry.find_profile("test_profile"), self.mock_profile)

    def test_find_profile(self):
        self.registry.add_profile(self.mock_profile)

        retrieved_profile = self.registry.find_profile("test_profile")

        self.assertEqual(retrieved_profile, self.mock_profile)

    def test_find_nonexistent_profile(self):
        self.assertIsNone(self.registry.find_profile("nonexistent"))

    def test_profiles(self):
        self.registry.add_profile(self.mock_profile)

        self.assertIn(self.mock_profile, self.registry.profiles)

    def test_get_requirements(self):
        feature_requirement = RequirementDTO(code="FEATURE.REQ", version="1.0.0")
        other_feature_requirement = RequirementDTO(code="OTHER.FEATURE.REQ", version="1.0.0")
        feature = FeatureDTO(
            id="feature",
            version="1.0.0",
            path="",
            requirements=[feature_requirement],
        )
        other_feature = FeatureDTO(
            id="other_feature",
            version="1.0.0",
            path="",
            requirements=[other_feature_requirement],
        )
        profile = ProfileDTO(
            id="profile",
            version="1.0.0",
            path="",
            features=[feature, other_feature],
            capabilities=[],
        )

        self.assertEqual(
            self.registry.get_requirements(profile),
            [feature_requirement, other_feature_requirement],
        )

    def test_singleton(self):
        registry1 = ProfileRegistry()
        registry2 = ProfileRegistry()

        registry1.add_profile(self.mock_profile)

        self.assertIsNotNone(registry1.find_profile("test_profile"))
        self.assertIsNotNone(registry2.find_profile("test_profile"))

    def test_duplicate_version_error(self):
        """Test that adding a profile with duplicate version raises ValueError."""
        profile_v1 = Mock(spec=Profile)
        profile_v1.id = "test_profile"
        profile_v1.version = "1.0.0"
        profile_v1.path = "/path/v1"
        profile_v1.capabilities = []

        profile_v1_duplicate = Mock(spec=Profile)
        profile_v1_duplicate.id = "test_profile"
        profile_v1_duplicate.version = "1.0.0"
        profile_v1_duplicate.path = "/path/v1_duplicate"
        profile_v1_duplicate.capabilities = []

        self.registry.add_profile(profile_v1)

        with self.assertRaises(ValueError) as context:
            self.registry.add_profile(profile_v1_duplicate)

        self.assertIn("already exists", str(context.exception))

    def test_version_sorting(self):
        """Test that profiles are sorted by version."""
        profile_v2 = Mock(spec=Profile)
        profile_v2.id = "test_profile"
        profile_v2.version = "2.0.0"
        profile_v2.path = "/path/v2"
        profile_v2.capabilities = []

        profile_v1 = Mock(spec=Profile)
        profile_v1.id = "test_profile"
        profile_v1.version = "1.0.0"
        profile_v1.path = "/path/v1"
        profile_v1.capabilities = []

        profile_v10 = Mock(spec=Profile)
        profile_v10.id = "test_profile"
        profile_v10.version = "10.0.0"
        profile_v10.path = "/path/v10"
        profile_v10.capabilities = []

        # Add in non-version order
        self.registry.add_profile(profile_v2)
        self.registry.add_profile(profile_v1)
        self.registry.add_profile(profile_v10)

        # Latest should be v10
        self.assertEqual(self.registry.find_profile("test_profile"), profile_v10)

        # All profiles should be in the list
        profiles = [p for p in self.registry.profiles if p.id == "test_profile"]
        self.assertEqual(len(profiles), 3)

    def test_register_profile_ok(self):
        register_profile(self.mock_profile)
        try:
            self.assertIn(self.mock_profile, self.registry)
        finally:
            unregister_profile(self.mock_profile)

    def test_unregister_profile_ok(self):
        register_profile(self.mock_profile)
        unregister_profile(self.mock_profile)
        self.assertNotIn(self.mock_profile, self.registry)

    def test_unregister_profile_ignores_feature_dependency_requirements(self):
        requirement = RequirementDTO(code="PROFILE.DEPENDENCY.REMOVE.REQ", version="1.0.0")
        dependency = FeatureDTO(
            id="profile_dependency_remove_feature",
            version="1.0.0",
            path="",
            requirements=[requirement],
        )
        feature = FeatureDTO(
            id="profile_feature_without_requirements",
            version="1.0.0",
            path="",
            requirements=[],
            dependencies=[dependency],
        )
        profile = ProfileDTO(
            id="profile_without_own_requirements",
            version="1.0.0",
            path="",
            features=[feature],
            capabilities=[],
        )

        class DependencyRule(BaseRuleChecker):
            pass

        register_feature(dependency)
        register_profile(profile)
        register_requirements(requirement)(DependencyRule)

        try:
            unregister_profile(profile)

            self.assertNotIn(profile, self.registry)
            self.assertIn(dependency, FeatureRegistry())
            self.assertEqual(RequirementsRegistry().get_validator(requirement), DependencyRule)
        finally:
            unregister_requirements(DependencyRule)
            if profile in self.registry:
                unregister_profile(profile)
            unregister_feature(dependency)

    def test_register_profiles(self):
        register_profiles([self.mock_profile])
        try:
            self.assertIn(self.mock_profile, self.registry.profiles)
        finally:
            unregister_profiles([self.mock_profile])

    def test_unregister_profiles(self):
        register_profiles([self.mock_profile])
        unregister_profiles([self.mock_profile])
        self.assertNotIn(self.mock_profile, self.registry.profiles)

    def test_add_callback_ok(self):
        callback = unittest.mock.Mock()
        _subscription = add_registry_profile_callback(callback)
        register_profile(self.mock_profile)
        try:
            callback.assert_called_once()
        finally:
            unregister_profile(self.mock_profile)
