# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import json
import tempfile
import unittest
from pathlib import Path

from usd_profiles_nvidia import LoadedSpecifications, SpecificationsLoader
from usd_profiles_nvidia.api import (
    Capability,
    CapabilityProtocol,
    Feature,
    FeatureProtocol,
    FeatureRef,
    Profile,
    ProfileFeature,
    ProfileProtocol,
    Requirement,
    RequirementRef,
)
from usd_profiles_nvidia.descriptors import DescriptorError, DescriptorKind
from usd_profiles_nvidia.parsers import SpecificationsParser


class TestSpecificationsLoader(unittest.TestCase):
    def test_root_dir_loads_json_profile_descriptor(self):
        root_dir = Path(__file__).parent / "resources" / "simple-spec"

        specifications = SpecificationsLoader(root_dir=root_dir).load()

        self.assertEqual([profile.id for profile in specifications.profiles], ["descriptor_profile"])
        self.assertEqual(
            specifications.profiles[0].features,
            [FeatureRef("descriptor_feature", "1.0.0")],
        )

    def test_loads_docs_tree_as_public_dtos_with_lazy_refs(self):
        root_dir = Path(__file__).parent / "resources" / "namespace-spec"

        specifications = SpecificationsLoader(root_dir=root_dir).load()

        self.assertIsInstance(specifications, LoadedSpecifications)
        self.assertTrue(specifications.capabilities)
        self.assertTrue(specifications.features)
        self.assertTrue(specifications.profiles)
        self.assertTrue(specifications.requirements)
        self.assertTrue(all(isinstance(value, Capability) for value in specifications.capabilities))
        self.assertTrue(all(isinstance(value, Feature) for value in specifications.features))
        self.assertTrue(all(isinstance(value, Profile) for value in specifications.profiles))
        self.assertTrue(all(isinstance(value, CapabilityProtocol) for value in specifications.capabilities))
        self.assertTrue(all(isinstance(value, FeatureProtocol) for value in specifications.features))
        self.assertTrue(all(isinstance(value, ProfileProtocol) for value in specifications.profiles))

        profile = specifications.profiles[0]
        self.assertTrue(profile.path)
        self.assertTrue(profile.display_name)
        self.assertEqual(len(profile.profile_features), 1)
        self.assertIsInstance(profile.profile_features[0], ProfileFeature)
        self.assertIsInstance(profile.profile_features[0].feature, Feature | FeatureRef)
        self.assertEqual(profile.features, [profile.profile_features[0].feature])

    def test_capabilities_root_loads_qualified_requirement_definitions(self):
        capabilities_root = Path(__file__).parent / "resources" / "simple-spec" / "capabilities"

        specifications = SpecificationsLoader(
            capabilities_root=capabilities_root,
            reverse_domain="com.nvidia.simready",
        ).load()

        self.assertEqual(len(specifications.capabilities), 1)
        self.assertEqual(len(specifications.requirements), 1)
        requirement = specifications.requirements[0]
        self.assertIsInstance(requirement, Requirement)
        self.assertEqual(requirement.code, "com.nvidia.simready.VG.RTX.002")
        self.assertEqual(requirement.version, "1.0.0")
        self.assertEqual(requirement.path, "geometry/requirements/usdgeom-mesh-count")
        self.assertEqual(specifications.features, [])
        self.assertEqual(specifications.profiles, [])

    def test_loaded_requirements_preserve_definitions_and_lazy_refs(self):
        requirement = Requirement("LOCAL.001")
        requirement_ref = RequirementRef("external.REQ.001")
        specifications = LoadedSpecifications(
            capabilities=[
                Capability(
                    id="mixed",
                    version="1.0.0",
                    path="",
                    requirements=[requirement, requirement_ref],
                )
            ]
        )

        self.assertEqual(specifications.requirements, [requirement, requirement_ref])
        self.assertIs(specifications.requirements, specifications.requirements)

    def test_loads_toml_profiles_as_unresolved_feature_refs(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            descriptor = Path(tmpdirname) / "profiles.toml"
            descriptor.write_text(
                """
[Prop-Robotics-Physx]
"2.1.0" = {features = [
    {FET003_BASE_PHYSX = {version = "0.3.0"}},
    {FET004_BASE_PHYSX = {version = "0.3.0"}, optional = true},
]}
""".strip(),
                encoding="utf-8",
            )

            profiles = SpecificationsLoader(profiles_roots=[descriptor]).load().profiles

        self.assertEqual(
            profiles,
            [
                Profile(
                    id="Prop-Robotics-Physx",
                    version="2.1.0",
                    path="profiles.toml",
                    features=[
                        FeatureRef("FET003_BASE_PHYSX", "0.3.0"),
                        FeatureRef("FET004_BASE_PHYSX", "0.3.0"),
                    ],
                    profile_features=[
                        ProfileFeature(FeatureRef("FET003_BASE_PHYSX", "0.3.0")),
                        ProfileFeature(FeatureRef("FET004_BASE_PHYSX", "0.3.0"), optional=True),
                    ],
                )
            ],
        )

    def test_loads_json_profiles_recursively_in_deterministic_path_order(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            root = Path(tmpdirname)
            nested = root / "nested"
            nested.mkdir()
            (root / "z.json").write_text(
                json.dumps(
                    {
                        "id": "z-profile",
                        "version": "1.0.0",
                        "name": "Z Profile",
                        "description": "A JSON profile",
                        "features": [{"feature": "FET_Z@1.0.0", "optional": True}],
                    }
                ),
                encoding="utf-8",
            )
            (nested / "a.json").write_text(
                json.dumps(
                    {
                        "profile": {
                            "id": "a-profile",
                            "version": "1.0.0",
                            "features": [{"FET_A": {"version": "2.0.0"}}],
                        }
                    }
                ),
                encoding="utf-8",
            )

            profiles = SpecificationsLoader(profiles_roots=[root]).load().profiles

        self.assertEqual([profile.id for profile in profiles], ["a-profile", "z-profile"])
        self.assertEqual([profile.path for profile in profiles], ["nested/a.json", "z.json"])
        self.assertEqual(profiles[0].features, [FeatureRef("FET_A", "2.0.0")])
        self.assertEqual(profiles[1].features, [FeatureRef("FET_Z", "1.0.0")])
        self.assertEqual(profiles[0].profile_features, [ProfileFeature(FeatureRef("FET_A", "2.0.0"))])
        self.assertEqual(profiles[1].profile_features, [ProfileFeature(FeatureRef("FET_Z", "1.0.0"), optional=True)])
        self.assertEqual(profiles[1].display_name, "Z Profile")
        self.assertEqual(profiles[1].message, "A JSON profile")

    def test_loads_json_version_table_profile(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            descriptor = Path(tmpdirname) / "profiles.json"
            descriptor.write_text(
                json.dumps(
                    {
                        "Prop-Robotics-Physx": {
                            "2.1.0": {
                                "features": [
                                    {"FET003_BASE_PHYSX": {"version": "0.3.0"}},
                                ]
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            profile = SpecificationsLoader(profiles_roots=[descriptor]).load().profiles[0]

        self.assertEqual(profile.id, "Prop-Robotics-Physx")
        self.assertEqual(profile.version, "2.1.0")
        self.assertEqual(profile.features, [FeatureRef("FET003_BASE_PHYSX", "0.3.0")])
        self.assertEqual(
            profile.profile_features,
            [ProfileFeature(FeatureRef("FET003_BASE_PHYSX", "0.3.0"))],
        )

    def test_enriches_profile_ids_and_feature_refs_with_reverse_domain(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            descriptor = Path(tmpdirname) / "profile.json"
            descriptor.write_text(
                json.dumps(
                    {
                        "id": "robotics",
                        "version": "1.0.0",
                        "features": [
                            {"feature": "physics@1.0.0"},
                            {"feature": "com.nvidia.simready.visual@2.0.0"},
                            {"feature": "org.example.external@3.0.0", "optional": True},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            profile = (
                SpecificationsLoader(
                    profiles_roots=[descriptor],
                    reverse_domain="com.nvidia.simready.",
                )
                .load()
                .profiles[0]
            )

        expected_features = [
            FeatureRef("com.nvidia.simready.physics", "1.0.0"),
            FeatureRef("com.nvidia.simready.visual", "2.0.0"),
            FeatureRef("org.example.external", "3.0.0"),
        ]
        self.assertEqual(profile.id, "com.nvidia.simready.robotics")
        self.assertEqual(profile.features, expected_features)
        self.assertEqual(
            profile.profile_features,
            [
                ProfileFeature(expected_features[0]),
                ProfileFeature(expected_features[1]),
                ProfileFeature(expected_features[2], optional=True),
            ],
        )

    def test_enriches_resolved_markdown_profile_features_with_reverse_domain(self):
        descriptor = Path(__file__).parent / "resources" / "simple-profile" / "profile-simple.md"

        profile = (
            SpecificationsLoader(
                profiles_roots=[descriptor],
                reverse_domain="com.nvidia.simready",
            )
            .load()
            .profiles[0]
        )

        self.assertEqual(profile.id, "com.nvidia.simready.name")
        self.assertEqual(
            [feature.id for feature in profile.features],
            ["com.nvidia.simready.simple", "com.nvidia.simready.complex"],
        )
        self.assertTrue(all(isinstance(feature, Feature) for feature in profile.features))
        self.assertEqual(
            [profile_feature.feature for profile_feature in profile.profile_features],
            profile.features,
        )
        self.assertTrue(
            all(
                feature.requirements == [RequirementRef("com.nvidia.simready.HI.001")]
                for feature in profile.features
                if isinstance(feature, Feature)
            )
        )

    def test_loads_version_table_profiles_with_layout_field_names_as_ids(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            descriptor = Path(tmpdirname) / "profiles.json"
            descriptor.write_text(
                json.dumps(
                    {
                        "id": {"1.0.0": {"features": []}},
                        "profile": {"2.0.0": {"features": []}},
                    }
                ),
                encoding="utf-8",
            )

            profiles = SpecificationsLoader(profiles_roots=[descriptor]).load().profiles

        self.assertEqual(
            [(profile.id, profile.version) for profile in profiles], [("id", "1.0.0"), ("profile", "2.0.0")]
        )

    def test_invalid_profile_descriptor_reports_source_path_once(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            descriptor = Path(tmpdirname) / "profile.json"
            descriptor.write_text(json.dumps({"id": "missing-version"}), encoding="utf-8")

            with self.assertRaises(DescriptorError) as context:
                SpecificationsLoader(profiles_roots=[descriptor]).load()

        self.assertEqual(context.exception.path, str(descriptor))
        self.assertEqual(context.exception.kind, DescriptorKind.PROFILE)
        self.assertEqual(str(context.exception).count("Invalid profile descriptor"), 1)
        self.assertIn(str(descriptor), str(context.exception))

    def test_parser_and_loader_report_invalid_descriptor_path_once(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            root_dir = Path(tmpdirname)
            features_dir = root_dir / "features"
            features_dir.mkdir()
            descriptor = features_dir / "invalid.toml"
            descriptor.write_text('id = "invalid"', encoding="utf-8")

            calls = [
                lambda: SpecificationsParser(root_dir=str(root_dir)).parse(),
                lambda: SpecificationsLoader(features_roots=[features_dir]).load(),
            ]
            for call in calls:
                with self.subTest(call=call):
                    with self.assertRaises(DescriptorError) as context:
                        call()
                    message = str(context.exception)
                    self.assertEqual(context.exception.path, str(descriptor))
                    self.assertEqual(context.exception.kind, DescriptorKind.FEATURE)
                    self.assertEqual(message.count("Invalid feature descriptor"), 1)
                    self.assertIn(str(descriptor), message)

    def test_loads_simready_json_as_reference_dtos(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            descriptor = Path(tmpdirname) / "feature.json"
            descriptor.write_text(
                json.dumps(
                    {
                        "id": "FET003_BASE_PHYSX",
                        "version": "0.1.0",
                        "display_name": "Rigid Body Physics",
                        "path": "features/FET_003-rigid_body_physics.html",
                        "dependencies": [{"FET003_BASE_NEUTRAL": {"version": "0.1.0"}}],
                        "requirements": ["COL.001"],
                        "ui_category": "Physics",
                    }
                ),
                encoding="utf-8",
            )

            specifications = SpecificationsLoader(
                features_roots=[descriptor],
                reverse_domain="com.nvidia.simready",
            ).load()

        self.assertIsInstance(specifications, LoadedSpecifications)
        self.assertEqual(
            specifications.features,
            [
                Feature(
                    id="FET003_BASE_PHYSX",
                    version="0.1.0",
                    path="features/FET_003-rigid_body_physics.html",
                    requirements=[RequirementRef("com.nvidia.simready.COL.001")],
                    dependencies=[FeatureRef("FET003_BASE_NEUTRAL", "0.1.0")],
                    custom_data={
                        "display_name": "Rigid Body Physics",
                        "ui_category": "Physics",
                    },
                )
            ],
        )

    def test_loads_toml_and_qualifies_refs_missing_reverse_domain_prefix(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            descriptor = Path(tmpdirname) / "feature.toml"
            descriptor.write_text(
                """
id = "FET_TOML"
version = "1.0.0"
display_name = "TOML Feature"
path = "features/toml.html"
requirements = [
    "COL.001@0.2.0",
    "VG.RTX.002",
    "com.nvidia.simready",
    "com.nvidia.simready.EXT.001",
    "com.nvidia.usd.AA.001",
    "org.example.AA.001",
    {code = "MAT.001", version = "1.0.0"},
]
dependencies = [
    {id = "FET_BASE", version = "0.1.0"},
]

[ui]
icon = "physics"
""".strip(),
                encoding="utf-8",
            )

            feature = (
                SpecificationsLoader(
                    features_roots=[descriptor],
                    reverse_domain="com.nvidia.simready.",
                )
                .load()
                .features[0]
            )

        self.assertEqual(
            feature.requirements,
            [
                RequirementRef("com.nvidia.simready.COL.001", "0.2.0"),
                RequirementRef("com.nvidia.simready.VG.RTX.002"),
                RequirementRef("com.nvidia.simready"),
                RequirementRef("com.nvidia.simready.EXT.001"),
                RequirementRef("com.nvidia.usd.AA.001"),
                RequirementRef("org.example.AA.001"),
                RequirementRef("com.nvidia.simready.MAT.001", "1.0.0"),
            ],
        )
        self.assertEqual(feature.dependencies, [FeatureRef("FET_BASE", "0.1.0")])
        self.assertEqual(
            feature.custom_data,
            {
                "display_name": "TOML Feature",
                "ui": {"icon": "physics"},
            },
        )

    def test_directory_parsing_is_recursive_and_deterministic(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            root = Path(tmpdirname)
            nested = root / "nested"
            nested.mkdir()
            (root / "z.json").write_text(
                json.dumps({"id": "z", "version": "1.0.0", "requirements": []}),
                encoding="utf-8",
            )
            (root / "a.toml").write_text(
                'id = "a"\nversion = "1.0.0"\nrequirements = []\n',
                encoding="utf-8",
            )
            nested_descriptor = nested / "b.json"
            nested_descriptor.write_text(
                json.dumps({"id": "b", "version": "1.0.0", "requirements": []}),
                encoding="utf-8",
            )
            (root / "ignored.txt").write_text("ignored", encoding="utf-8")

            features = (
                SpecificationsLoader(
                    features_roots=[root],
                    reverse_domain="com.nvidia.simready",
                )
                .load()
                .features
            )

        self.assertEqual([feature.id for feature in features], ["a", "b", "z"])

    def test_loads_markdown_through_specifications_parser_and_enriches_refs(self):
        root_dir = Path(__file__).parent / "resources" / "simple-feature"

        feature = (
            SpecificationsLoader(
                features_roots=[root_dir],
                reverse_domain="com.nvidia.simready",
            )
            .load()
            .features[0]
        )

        self.assertEqual(feature.id, "example")
        self.assertEqual(feature.path, "example")
        self.assertEqual(
            feature.requirements,
            [RequirementRef("com.nvidia.simready.HI.001")],
        )

    def test_missing_requirement_definitions_do_not_prevent_loading(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            descriptor = Path(tmpdirname) / "missing.json"
            descriptor.write_text(
                json.dumps(
                    {
                        "id": "missing",
                        "version": "1.0.0",
                        "requirements": ["MISSING.999"],
                    }
                ),
                encoding="utf-8",
            )

            features = (
                SpecificationsLoader(
                    features_roots=[descriptor],
                    reverse_domain="com.nvidia.simready",
                )
                .load()
                .features
            )

        self.assertEqual(
            features[0].requirements,
            [RequirementRef("com.nvidia.simready.MISSING.999")],
        )

    def test_existing_specifications_parser_includes_toml_features(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            root_dir = Path(tmpdirname)
            features_dir = root_dir / "features"
            features_dir.mkdir()
            (features_dir / "feature.toml").write_text(
                """
id = "toml"
version = "1.0.0"
requirements = ["REQ.001"]
""".strip(),
                encoding="utf-8",
            )

            specifications = SpecificationsParser(root_dir=str(root_dir)).parse()

        self.assertEqual(len(specifications.features), 1)
        self.assertEqual(specifications.features[0].id, "toml")
        self.assertEqual(specifications.features[0].requirements, [RequirementRef("REQ.001")])

    def test_existing_specifications_parser_ignores_unrelated_toml_in_profiles_directory(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            root_dir = Path(tmpdirname)
            profiles_dir = root_dir / "profiles"
            profiles_dir.mkdir()
            (profiles_dir / "pyproject.toml").write_text(
                '[project]\nname = "not-a-profile"',
                encoding="utf-8",
            )
            (profiles_dir / "profiles.toml").write_text(
                '[Example]\n"1.0.0" = {features = []}',
                encoding="utf-8",
            )

            specifications = SpecificationsParser(root_dir=str(root_dir)).parse()

        self.assertEqual([profile.id for profile in specifications.profiles], ["Example"])
