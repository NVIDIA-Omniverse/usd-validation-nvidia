# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

import unittest
from dataclasses import dataclass

from usd_validation_nvidia import (
    CapabilityRegistry,
    FeatureRegistry,
    ProfileRegistry,
    RequirementsRegistry,
    register_content,
    unregister_content,
)
from usd_validation_nvidia.capabilities import Capability as CapabilityDTO
from usd_validation_nvidia.capabilities import Feature as FeatureDTO
from usd_validation_nvidia.capabilities import FeatureRef as FeatureRefDTO
from usd_validation_nvidia.capabilities import Profile as ProfileDTO
from usd_validation_nvidia.capabilities import ProfileFeature
from usd_validation_nvidia.capabilities import Requirement as RequirementDTO
from usd_validation_nvidia.capabilities import RequirementRef as RequirementRefDTO


@dataclass(frozen=True)
class LoadedContent:
    capabilities: list[CapabilityDTO]
    features: list[FeatureDTO]
    profiles: list[ProfileDTO]

    @property
    def requirements(self) -> list[RequirementDTO | RequirementRefDTO]:
        return [requirement for capability in self.capabilities for requirement in capability.requirements]


class RegisterContentTest(unittest.TestCase):
    def setUp(self):
        self.requirement = RequirementDTO(code="com.example.CONTENT.001", version="1.0.0")
        self.capability = CapabilityDTO(
            id="com.example.content.capability",
            version="1.0.0",
            path="capabilities/content-capability.html",
            requirements=[self.requirement],
        )
        self.feature = FeatureDTO(
            id="com.example.content.feature",
            version="1.0.0",
            path="features/content-feature.html",
            requirements=[],
        )
        self.profile = ProfileDTO(
            id="com.example.content.profile",
            version="1.0.0",
            path="profiles/content-profile.html",
            features=[self.feature],
            capabilities=[self.capability],
        )
        self.content = LoadedContent(
            capabilities=[self.capability],
            features=[self.feature],
            profiles=[self.profile],
        )

    def tearDown(self):
        unregister_content(self.content)

    def test_register_content_registers_requirements_capabilities_features_and_profiles(self):
        self.assertIsNone(register_content(self.content))

        self.assertIs(
            RequirementsRegistry().find_requirement(self.requirement.code, self.requirement.version),
            self.requirement,
        )
        self.assertIs(CapabilityRegistry().find(self.capability.id, self.capability.version), self.capability)
        self.assertIs(FeatureRegistry().find(self.feature.id, self.feature.version), self.feature)
        self.assertIs(ProfileRegistry().find(self.profile.id, self.profile.version), self.profile)

    def test_unregister_content_unregisters_requirements_capabilities_features_and_profiles(self):
        register_content(self.content)

        self.assertIsNone(unregister_content(self.content))

        self.assertIsNone(RequirementsRegistry().find_requirement(self.requirement.code, self.requirement.version))
        self.assertIsNone(CapabilityRegistry().find(self.capability.id, self.capability.version))
        self.assertIsNone(FeatureRegistry().find(self.feature.id, self.feature.version))
        self.assertIsNone(ProfileRegistry().find(self.profile.id, self.profile.version))

    def test_register_content_preserves_unresolved_refs(self):
        requirement_ref = RequirementRefDTO(code="com.example.UNRESOLVED.001", version="1.0.0")
        capability = CapabilityDTO(
            id="com.example.content.capability.refs",
            version="1.0.0",
            path="capabilities/content-capability-refs.html",
            requirements=[requirement_ref],
        )
        feature = FeatureDTO(
            id="com.example.content.feature.refs",
            version="1.0.0",
            path="features/content-feature-refs.html",
            requirements=[requirement_ref],
        )
        profile = ProfileDTO(
            id="com.example.content.profile.refs",
            version="1.0.0",
            path="profiles/content-profile-refs.html",
            profile_features=[
                ProfileFeature(FeatureRefDTO(id="com.example.content.unresolved-feature", version="1.0.0"))
            ],
        )
        content = LoadedContent(
            capabilities=[capability],
            features=[feature],
            profiles=[profile],
        )

        try:
            register_content(content)

            self.assertIsNone(RequirementsRegistry().find_requirement(requirement_ref.code, requirement_ref.version))
            self.assertIs(CapabilityRegistry().find(capability.id, capability.version), capability)
            self.assertIs(FeatureRegistry().find(feature.id, feature.version), feature)
            self.assertIs(ProfileRegistry().find(profile.id, profile.version), profile)
        finally:
            unregister_content(content)


if __name__ == "__main__":
    unittest.main()
