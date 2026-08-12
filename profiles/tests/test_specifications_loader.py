# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import json
import tempfile
import unittest
from pathlib import Path

from usd_profiles_nvidia import LoadedSpecifications, SpecificationsLoader
from usd_profiles_nvidia.api import Feature, FeatureRef, RequirementRef
from usd_profiles_nvidia.descriptors import FeatureDescriptorError
from usd_profiles_nvidia.parsers import SpecificationsParser


class TestSpecificationsLoader(unittest.TestCase):
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
                    with self.assertRaises(FeatureDescriptorError) as context:
                        call()
                    message = str(context.exception)
                    self.assertEqual(context.exception.path, str(descriptor))
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

            feature = SpecificationsLoader(
                features_roots=[descriptor],
                reverse_domain="com.nvidia.simready.",
            ).load().features[0]

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

            features = SpecificationsLoader(
                features_roots=[root],
                reverse_domain="com.nvidia.simready",
            ).load().features

        self.assertEqual([feature.id for feature in features], ["a", "b", "z"])

    def test_loads_markdown_through_specifications_parser_and_enriches_refs(self):
        root_dir = Path(__file__).parent / "resources" / "simple-feature"

        feature = SpecificationsLoader(
            features_roots=[root_dir],
            reverse_domain="com.nvidia.simready",
        ).load().features[0]

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

            features = SpecificationsLoader(
                features_roots=[descriptor],
                reverse_domain="com.nvidia.simready",
            ).load().features

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
