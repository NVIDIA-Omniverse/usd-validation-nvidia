# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest

from usd_profiles_nvidia import (
    LoadedSpecifications,
    LoadedSpecificationsProtocol,
    SpecificationKind,
    SpecificationProblemKind,
    SpecificationProblemSeverity,
)
from usd_profiles_nvidia.api import (
    Capability,
    Feature,
    FeatureRef,
    Profile,
    ProfileFeature,
    Requirement,
    RequirementRef,
)


class TestSpecificationDiagnostics(unittest.TestCase):
    def test_loaded_specifications_implements_runtime_protocol(self):
        self.assertIsInstance(LoadedSpecifications(), LoadedSpecificationsProtocol)

    def test_validate_returns_typed_structural_problems(self):
        requirement = Requirement("REQ.001", "1.0.0", path="requirements/req-001.md")
        duplicate_requirement = Requirement("REQ.001", "1.0.0", path="requirements/duplicate.md")
        capability = Capability(
            "capability",
            "1.0.0",
            "capabilities/capability.md",
            [requirement, duplicate_requirement],
        )
        feature = Feature(
            "feature",
            "invalid",
            "features/feature.json",
            requirements=[RequirementRef("EXT.001", "bad")],
            dependencies=[FeatureRef("dependency", "also-bad")],
        )
        profile = Profile(
            "profile",
            "1.0.0",
            "profiles/profile.toml",
            profile_features=[ProfileFeature(FeatureRef("feature", "1.0.0"), optional="yes")],
        )
        specifications = LoadedSpecifications(
            capabilities=[capability],
            features=[feature, feature],
            profiles=[profile, profile],
        )

        problems = specifications.validate()

        self.assertTrue(all(problem.severity is SpecificationProblemSeverity.ERROR for problem in problems))
        self.assertEqual(
            [problem.kind for problem in problems],
            [
                SpecificationProblemKind.DUPLICATE_REQUIREMENT,
                SpecificationProblemKind.DUPLICATE_FEATURE,
                SpecificationProblemKind.DUPLICATE_PROFILE,
                SpecificationProblemKind.MALFORMED_VERSION,
                SpecificationProblemKind.MALFORMED_VERSION,
                SpecificationProblemKind.MALFORMED_VERSION,
                SpecificationProblemKind.INVALID_PROFILE_FEATURE_OPTIONALITY,
            ],
        )
        self.assertEqual(problems[0].source.kind, SpecificationKind.REQUIREMENT)
        self.assertEqual(problems[0].source.source_label, "requirements/duplicate.md")
        self.assertEqual(problems[3].source.kind, SpecificationKind.FEATURE)
        self.assertEqual(problems[4].reference.kind, SpecificationKind.REQUIREMENT)
        self.assertIsNone(problems[4].reference.source_label)
        self.assertEqual(problems[-1].source.source_label, "profiles/profile.toml")

    def test_validate_does_not_resolve_or_mutate_references(self):
        requirement_ref = RequirementRef("external.REQ.001", "1.0.0")
        dependency_ref = FeatureRef("external.dependency", "1.0.0")
        profile_ref = FeatureRef("external.feature", "1.0.0")
        feature = Feature(
            "feature",
            "1.0.0",
            "features/feature.json",
            requirements=[requirement_ref],
            dependencies=[dependency_ref],
        )
        profile_feature = ProfileFeature(profile_ref, optional=True)
        profile = Profile(
            "profile",
            "1.0.0",
            "profiles/profile.json",
            features=[profile_ref],
            profile_features=[profile_feature],
        )
        specifications = LoadedSpecifications(features=[feature], profiles=[profile])

        self.assertEqual(specifications.validate(), ())

        self.assertIs(feature.requirements[0], requirement_ref)
        self.assertIs(feature.dependencies[0], dependency_ref)
        self.assertIs(profile.features[0], profile_ref)
        self.assertIs(profile.profile_features[0], profile_feature)
        self.assertIs(profile.profile_features[0].feature, profile_ref)

    def test_validate_normalizes_versions_when_finding_duplicates(self):
        first = Feature("feature", "1", "features/first.json")
        second = Feature("feature", "1.0.0", "features/second.json")

        problems = LoadedSpecifications(features=[first, second]).validate()

        self.assertEqual(len(problems), 1)
        self.assertEqual(problems[0].kind, SpecificationProblemKind.DUPLICATE_FEATURE)
        self.assertEqual(problems[0].source.version, "1.0.0")


if __name__ == "__main__":
    unittest.main()
