# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import json
import tempfile
import unittest
from pathlib import Path

from usd_profiles_nvidia.api import FeatureRef, RequirementRef
from usd_profiles_nvidia.descriptors import FeatureDescriptorError
from usd_profiles_nvidia.json import JsonFeaturesParser
from usd_profiles_nvidia.markdown import FeaturesParser
from usd_profiles_nvidia.parsers import FeaturesParser as AllFeaturesParser
from usd_profiles_nvidia.toml import TomlFeaturesParser


class TestFeaturesParser(unittest.TestCase):
    def test_format_parsers_report_invalid_descriptor_source_path(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            root_dir = Path(tmpdirname)
            json_path = root_dir / "invalid.json"
            toml_path = root_dir / "invalid.toml"
            markdown_path = root_dir / "invalid.md"
            json_path.write_text('{"version": "1.0.0"}', encoding="utf-8")
            toml_path.write_text('id = "invalid"', encoding="utf-8")
            markdown_path.write_text(
                """
# Invalid

| **Property** | **Value** |
|--------------|-----------|
| Dependency   | OpenUSD   |

## Requirements

```{features-table}
REQ.001
```
""".strip(),
                encoding="utf-8",
            )

            parsers = [
                (JsonFeaturesParser(root_dir=str(root_dir), path=str(json_path)), json_path),
                (TomlFeaturesParser(root_dir=str(root_dir), path=str(toml_path)), toml_path),
                (FeaturesParser(root_dir=str(root_dir), path=str(markdown_path)), markdown_path),
            ]
            for parser, source_path in parsers:
                with self.subTest(source_path=source_path):
                    with self.assertRaises(FeatureDescriptorError) as context:
                        parser.parse()
                    self.assertEqual(context.exception.path, str(source_path))
                    self.assertIn(str(source_path), str(context.exception))

    def test_parse_ok(self):
        root_dir = Path(__file__).parent / "resources" / "simple-feature"
        parser = FeaturesParser(root_dir=str(root_dir), path=str(root_dir))
        features = parser.parse()

        self.assertEqual(len(features), 1)
        self.assertEqual(features[0].id, "example")
        self.assertEqual(features[0].version, "1.0.0")
        self.assertEqual(features[0].path, "example")
        self.assertEqual(features[0].requirements, [RequirementRef("HI.001")])

    def test_parse_with_options_ok(self):
        root_dir = Path(__file__).parent / "resources" / "simple-feature-options"
        parser = FeaturesParser(root_dir=str(root_dir), path=str(root_dir))
        features = parser.parse()

        self.assertEqual(len(features), 1)
        self.assertEqual(features[0].id, "example")
        self.assertEqual(features[0].version, "1.0.0")
        self.assertEqual(features[0].path, "example")
        self.assertEqual(features[0].requirements, [RequirementRef("HI.001"), RequirementRef("HI.002")])

    def test_parse_with_extends_ok(self):
        root_dir = Path(__file__).parent / "resources" / "simple-feature-extends"
        parser = FeaturesParser(root_dir=str(root_dir), path=str(root_dir))
        features = parser.parse()

        self.assertEqual(len(features), 2)
        base, extended = sorted(features, key=lambda f: f.version or "0.0.0")
        self.assertEqual(base.id, "base")
        self.assertEqual(base.version, "1.0.0")
        self.assertEqual(
            base.requirements,
            [RequirementRef("A", "1.0.0"), RequirementRef("B", "1.0.0")],
        )
        self.assertEqual(extended.id, "extended")
        self.assertEqual(extended.version, "1.1.0")
        self.assertFalse(hasattr(extended, "extends"))

    def test_parse_with_dependencies_ok(self):
        root_dir = Path(__file__).parent / "resources" / "simple-feature-dependencies"
        parser = FeaturesParser(root_dir=str(root_dir), path=str(root_dir))
        features = parser.parse()

        self.assertEqual(len(features), 1)
        self.assertEqual(features[0].id, "dependent")
        self.assertEqual(
            features[0].dependencies,
            [
                FeatureRef("base", "1.0.0"),
                FeatureRef("external.feature", "2.0.0"),
            ],
        )

    def test_parse_json_features_with_dependencies_ok(self):
        root_dir = Path(__file__).parent / "resources" / "feature-dependency-spec"
        parser = JsonFeaturesParser(root_dir=str(root_dir), path=str(root_dir / "features"))
        features = parser.parse()

        self.assertEqual(len(features), 3)
        by_id = {feature.id: feature for feature in features}
        self.assertEqual(
            by_id["FET003_BASE_PHYSX"].dependencies,
            [FeatureRef("FET003_BASE_NEUTRAL", "0.1.0")],
        )
        self.assertEqual(by_id["FET003_BASE_PHYSX"].path, "features/FET_003-rigid_body_physics.html")
        self.assertEqual(
            by_id["FET004_BASE_STRING_DEP"].dependencies,
            [FeatureRef("FET003_BASE_NEUTRAL", "0.1.0")],
        )
        self.assertEqual(by_id["FET004_BASE_STRING_DEP"].path, "features/FET_004-string_dependency.html")

    def test_parse_minimal_json_feature(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            root_dir = Path(tmpdirname)
            features_dir = root_dir / "features"
            features_dir.mkdir()
            (features_dir / "minimal.json").write_text(
                json.dumps({"id": "minimal", "version": "1.0.0", "requirements": ["REQ.001"]}),
                encoding="utf-8",
            )

            parser = JsonFeaturesParser(root_dir=str(root_dir), path=str(features_dir))
            features = parser.parse()

        self.assertEqual(len(features), 1)
        self.assertEqual(features[0].id, "minimal")
        self.assertEqual(features[0].version, "1.0.0")
        self.assertEqual(features[0].requirements, [RequirementRef("REQ.001")])
        self.assertEqual(features[0].path, "features/minimal")

    def test_format_agnostic_parser_includes_json_features_ok(self):
        root_dir = Path(__file__).parent / "resources" / "feature-dependency-spec"
        parser = AllFeaturesParser(root_dir=str(root_dir), path=str(root_dir / "features"))
        features = parser.parse()

        self.assertEqual(len(features), 3)

    def test_json_and_toml_file_parsers_share_descriptor_decoding(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            root_dir = Path(tmpdirname)
            json_path = root_dir / "feature.json"
            toml_path = root_dir / "feature.toml"
            json_path.write_text(
                json.dumps(
                    {
                        "id": "shared",
                        "version": "1.0.0",
                        "display_name": "Shared Decoder",
                        "path": "features/shared.html",
                        "requirements": ["REQ.001@1.0.0", "org.example.EXT.001"],
                        "dependencies": [{"base": {"version": "0.1.0"}}],
                        "custom_data": {"source": "authored"},
                        "ui": {"icon": "shared"},
                    }
                ),
                encoding="utf-8",
            )
            toml_path.write_text(
                """
id = "shared"
version = "1.0.0"
display_name = "Shared Decoder"
path = "features/shared.html"
requirements = ["REQ.001@1.0.0", "org.example.EXT.001"]
dependencies = [{base = {version = "0.1.0"}}]

[custom_data]
source = "authored"

[ui]
icon = "shared"
""".strip(),
                encoding="utf-8",
            )

            json_feature = JsonFeaturesParser(
                root_dir=str(root_dir),
                path=str(root_dir),
            ).parse()[0]
            toml_feature = TomlFeaturesParser(
                root_dir=str(root_dir),
                path=str(root_dir),
            ).parse()[0]

        self.assertEqual(json_feature, toml_feature)
        self.assertEqual(
            json_feature.requirements,
            [
                RequirementRef("REQ.001", "1.0.0"),
                RequirementRef("org.example.EXT.001"),
            ],
        )
        self.assertEqual(json_feature.dependencies, [FeatureRef("base", "0.1.0")])
        self.assertEqual(
            json_feature.custom_data,
            {
                "display_name": "Shared Decoder",
                "source": "authored",
                "ui": {"icon": "shared"},
            },
        )

    def test_toml_directory_and_format_agnostic_parsers(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            root_dir = Path(tmpdirname)
            features_dir = root_dir / "features"
            features_dir.mkdir()
            (features_dir / "feature.toml").write_text(
                """
id = "toml"
version = "1.0.0"
path = "features/toml.html"
requirements = ["REQ.001"]
""".strip(),
                encoding="utf-8",
            )

            toml_features = TomlFeaturesParser(
                root_dir=str(root_dir),
                path=str(features_dir),
            ).parse()
            all_features = AllFeaturesParser(
                root_dir=str(root_dir),
                path=str(features_dir),
            ).parse()

        self.assertEqual(toml_features, all_features)
        self.assertEqual(len(all_features), 1)
        self.assertEqual(all_features[0].id, "toml")
        self.assertEqual(all_features[0].path, "features/toml.html")
        self.assertEqual(all_features[0].requirements, [RequirementRef("REQ.001")])

    def test_parse_with_requirements_sublist_ok(self):
        root_dir = Path(__file__).parent / "resources" / "simple-feature-links"
        parser = FeaturesParser(root_dir=str(root_dir), path=str(root_dir))
        features = parser.parse()

        self.assertEqual(len(features), 1)
        self.assertEqual(features[0].id, "example")
        self.assertEqual(features[0].version, "1.0.0")
        self.assertEqual(
            features[0].requirements,
            [RequirementRef("NP.001", "0.1.0")],
        )

    def test_parse_with_multi_version_ok(self):
        root_dir = Path(__file__).parent / "resources" / "simple-feature-multi-version"
        parser = FeaturesParser(root_dir=str(root_dir), path=str(root_dir / "example.md"))
        features = parser.parse()

        self.assertEqual(len(features), 2)
        by_version = sorted(features, key=lambda f: f.version)
        v01, v10 = by_version[0], by_version[1]
        self.assertEqual(v01.id, "FET_001")
        self.assertEqual(v01.version, "0.1.0")
        self.assertEqual(v01.requirements, [RequirementRef("NP.001", "0.1.0")])
        self.assertEqual(v10.id, "FET_001")
        self.assertEqual(v10.version, "1.0.0")
        self.assertEqual(v10.requirements, [RequirementRef("NP.001", "0.1.0")])
