# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest

from usd_validation_nvidia import (
    BaseRuleChecker,
    FeatureRegistry,
    ProfileRegistry,
    RequirementsRegistry,
    add_registry_profile_callback,
    register_capability,
    register_feature,
    register_profile,
    register_profiles,
    register_requirements,
    unregister_capability,
    unregister_feature,
    unregister_profile,
    unregister_profiles,
    unregister_requirements,
)
from usd_validation_nvidia.capabilities import Capability as CapabilityDTO
from usd_validation_nvidia.capabilities import Feature as FeatureDTO
from usd_validation_nvidia.capabilities import FeatureRef
from usd_validation_nvidia.capabilities import Profile as ProfileDTO
from usd_validation_nvidia.capabilities import ProfileFeature
from usd_validation_nvidia.capabilities import Requirement as RequirementDTO


class TestProfileRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = ProfileRegistry()
        self.profile = ProfileDTO(
            id="test_profile",
            version="1.0.0",
            path="/path/v1",
        )

    def tearDown(self):
        try:
            unregister_profile(self.profile)
        except ValueError:
            pass

    def test_add_profile(self):
        self.registry.add(self.profile)

        self.assertIn(self.profile, self.registry.profiles)
        self.assertEqual(self.registry.find("test_profile"), self.profile)

    def test_find_profile(self):
        self.registry.add(self.profile)

        retrieved_profile = self.registry.find("test_profile")

        self.assertEqual(retrieved_profile, self.profile)

    def test_find_nonexistent_profile(self):
        self.assertIsNone(self.registry.find("nonexistent"))

    def test_profiles(self):
        self.registry.add(self.profile)

        self.assertIn(self.profile, self.registry.profiles)

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

    def test_get_requirements_uses_legacy_features(self):
        requirement = RequirementDTO(code="FEATURE.REQ", version="1.0.0")
        feature = FeatureDTO(id="feature", version="1.0.0", path="", requirements=[requirement])
        profile = ProfileDTO(
            id="legacy-profile",
            version="1.0.0",
            path="",
            features=[feature],
        )

        self.assertEqual(self.registry.get_requirements(profile), [requirement])
        self.assertEqual(self.registry.get_requirements(profile, optional=False), [requirement])

    def test_get_requirements_resolves_profile_feature_refs_when_available(self):
        requirement = RequirementDTO(code="FEATURE.REQ", version="1.0.0")
        feature = FeatureDTO(id="feature", version="1.1.0", path="", requirements=[requirement])
        register_feature(feature)
        self.addCleanup(unregister_feature, feature)
        profile = ProfileDTO(
            id="profile-refs",
            version="1.0.0",
            path="",
            profile_features=[ProfileFeature(FeatureRef("feature", "1.1.0"))],
        )

        self.assertEqual(self.registry.get_requirements(profile), [requirement])

    def test_get_requirements_capability(self):
        requirement = RequirementDTO(code="CAPABILITY.REQ", version="1.0.0")
        capability = CapabilityDTO(
            id="capability",
            version="1.0.0",
            path="",
            requirements=[requirement],
        )
        profile = ProfileDTO(
            id="profile-capability",
            version="1.0.0",
            path="",
            capabilities=[capability],
        )

        self.assertEqual(self.registry.get_requirements(profile), [requirement])
        self.assertEqual(
            self.registry.get_requirements(profile, optional=False),
            [requirement],
        )

    def test_get_requirements_profile_features_mandatory(self):
        requirement = RequirementDTO(code="MANDATORY.FEATURE.REQ", version="1.0.0")
        feature = FeatureDTO(id="mandatory-feature", version="1.0.0", path="", requirements=[requirement])
        register_feature(feature)
        self.addCleanup(unregister_feature, feature)
        profile = ProfileDTO(
            id="profile-mandatory",
            version="1.0.0",
            path="",
            profile_features=[ProfileFeature(FeatureRef(feature.id, feature.version))],
        )

        self.assertEqual(profile.features, [])
        self.assertEqual(profile.capabilities, [])
        self.assertEqual(self.registry.get_requirements(profile), [requirement])
        self.assertEqual(self.registry.get_requirements(profile, optional=False), [requirement])

    def test_get_requirements_profile_features_optional(self):
        requirement = RequirementDTO(code="OPTIONAL.FEATURE.REQ", version="1.0.0")
        feature = FeatureDTO(id="optional-feature", version="1.0.0", path="", requirements=[requirement])
        register_feature(feature)
        self.addCleanup(unregister_feature, feature)
        profile = ProfileDTO(
            id="profile-optional",
            version="1.0.0",
            path="",
            profile_features=[ProfileFeature(FeatureRef(feature.id, feature.version), optional=True)],
        )

        self.assertEqual(self.registry.get_requirements(profile), [requirement])
        self.assertEqual(self.registry.get_requirements(profile, optional=False), [])

    def test_get_requirements_profile_feature_ref_capability(self):
        requirement = RequirementDTO(code="PROFILE.FEATURE.CAPABILITY.REQ", version="1.0.0")
        capability = CapabilityDTO(
            id="capability-backed-feature",
            version="1.0.0",
            path="",
            requirements=[requirement],
        )
        register_capability(capability)
        self.addCleanup(unregister_capability, capability)
        profile = ProfileDTO(
            id="profile-capability-backed-feature",
            version="1.0.0",
            path="",
            profile_features=[ProfileFeature(FeatureRef(capability.id, capability.version))],
        )

        self.assertEqual(profile.features, [])
        self.assertEqual(profile.capabilities, [])
        self.assertEqual(self.registry.get_requirements(profile), [requirement])
        self.assertEqual(self.registry.get_requirements(profile, optional=False), [requirement])

    def test_get_requirements_profile_features_dependencies(self):
        dependency_requirement = RequirementDTO(code="DEPENDENCY.FEATURE.REQ", version="1.0.0")
        requirement = RequirementDTO(code="FEATURE.REQ", version="1.0.0")
        dependency = FeatureDTO(
            id="dependency-feature",
            version="1.0.0",
            path="",
            requirements=[dependency_requirement],
        )
        feature = FeatureDTO(
            id="feature",
            version="1.0.0",
            path="",
            requirements=[requirement],
            dependencies=[FeatureRef(dependency.id, dependency.version)],
        )
        for registered_feature in (dependency, feature):
            register_feature(registered_feature)
            self.addCleanup(unregister_feature, registered_feature)
        profile = ProfileDTO(
            id="profile-dependencies",
            version="1.0.0",
            path="",
            profile_features=[ProfileFeature(FeatureRef(feature.id, feature.version))],
        )

        self.assertEqual(self.registry.get_requirements(profile), [requirement, dependency_requirement])
        self.assertEqual(self.registry.get_requirements(profile, optional=False), [requirement, dependency_requirement])
        self.assertEqual(self.registry.get_requirements(profile, recursive=False), [requirement])
        self.assertEqual(self.registry.get_requirements(profile, optional=False, recursive=False), [requirement])

    def test_get_requirements_rejects_unresolved_required_profile_feature_refs(self):
        profile = ProfileDTO(
            id="profile-refs",
            version="1.0.0",
            path="",
            profile_features=[ProfileFeature(FeatureRef("unavailable", "1.0.0"))],
        )

        with self.assertRaisesRegex(
            ValueError,
            "Required feature 'unavailable' version '1.0.0'.*profile 'profile-refs' version '1.0.0'",
        ):
            self.registry.get_requirements(profile)

    def test_get_requirements_ignores_unresolved_optional_profile_feature_refs(self):
        profile = ProfileDTO(
            id="profile-refs",
            version="1.0.0",
            path="",
            profile_features=[ProfileFeature(FeatureRef("unavailable", "1.0.0"), optional=True)],
        )

        self.assertEqual(self.registry.get_requirements(profile), [])

    def test_unresolved_profile_feature_ref_does_not_prevent_removal(self):
        profile = ProfileDTO(
            id="profile-unresolved-removal",
            version="1.0.0",
            path="",
            profile_features=[ProfileFeature(FeatureRef("unavailable", "1.0.0"))],
        )
        self.registry.add(profile)

        self.registry.remove(profile)

        self.assertIsNone(self.registry.find(profile.id, profile.version))

    def test_singleton(self):
        registry1 = ProfileRegistry()
        registry2 = ProfileRegistry()

        registry1.add(self.profile)

        self.assertIsNotNone(registry1.find("test_profile"))
        self.assertIsNotNone(registry2.find("test_profile"))

    def test_duplicate_version_error(self):
        """Test that adding a profile with duplicate version raises ValueError."""
        profile_v1 = ProfileDTO(id="test_profile", version="1.0.0", path="/path/v1")
        profile_v1_duplicate = ProfileDTO(id="test_profile", version="1.0.0", path="/path/v1_duplicate")

        self.registry.add(profile_v1)

        with self.assertRaises(ValueError) as context:
            self.registry.add(profile_v1_duplicate)

        self.assertIn("already exists", str(context.exception))

    def test_version_sorting(self):
        """Test that profiles are sorted by version."""
        profile_v2 = ProfileDTO(id="test_profile", version="2.0.0", path="/path/v2")
        profile_v1 = ProfileDTO(id="test_profile", version="1.0.0", path="/path/v1")
        profile_v10 = ProfileDTO(id="test_profile", version="10.0.0", path="/path/v10")

        # Add in non-version order
        self.registry.add(profile_v2)
        self.registry.add(profile_v1)
        self.registry.add(profile_v10)

        # Latest should be v10
        self.assertEqual(self.registry.find("test_profile"), profile_v10)

        # All profiles should be in the list
        profiles = [p for p in self.registry.profiles if p.id == "test_profile"]
        self.assertEqual(len(profiles), 3)

    def test_register_profile_ok(self):
        register_profile(self.profile)
        try:
            self.assertIn(self.profile, self.registry)
        finally:
            unregister_profile(self.profile)

    def test_unregister_profile_ok(self):
        register_profile(self.profile)
        unregister_profile(self.profile)
        self.assertNotIn(self.profile, self.registry)

    def test_unregister_profile_requirement_ok(self):
        requirement = RequirementDTO(code="PROFILE.REMOVE.REQ", version="1.0.0")
        feature = FeatureDTO(
            id="profile_implemented_requirement_feature",
            version="1.0.0",
            path="",
            requirements=[requirement],
        )
        profile = ProfileDTO(
            id="implemented_requirement_profile",
            version="1.0.0",
            path="/path/original",
            features=[feature],
        )

        class ProfileRule(BaseRuleChecker):
            pass

        register_requirements(requirement)(ProfileRule)
        register_profile(profile)

        try:
            unregister_profile(profile)

            self.assertNotIn(profile, self.registry)
        finally:
            unregister_requirements(ProfileRule)

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
        self.assertTrue(register_profiles([self.profile]))
        try:
            self.assertIn(self.profile, self.registry.profiles)
        finally:
            unregister_profiles([self.profile])

    def test_register_profiles_duplicate_returns_false(self):
        register_profile(self.profile)
        try:
            self.assertFalse(register_profiles([self.profile]))
        finally:
            unregister_profile(self.profile)

    def test_unregister_profiles(self):
        register_profiles([self.profile])
        self.assertTrue(unregister_profiles([self.profile]))
        self.assertNotIn(self.profile, self.registry.profiles)

    def test_add_callback_ok(self):
        callback = unittest.mock.Mock()
        _subscription = add_registry_profile_callback(callback)
        register_profile(self.profile)
        try:
            callback.assert_called_once()
        finally:
            unregister_profile(self.profile)
