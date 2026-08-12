# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import json
import unittest

from usd_profiles_nvidia.api import Capability, Feature, FeatureRef, Requirement, RequirementRef
from usd_profiles_nvidia.json import (
    JsonDeserialize,
)
from usd_profiles_nvidia.model import (
    Compatibility,
    Example,
    ExampleResult,
    ExampleSnippet,
    ExampleSnippetLanguage,
    IdVersion,
    Metadata,
    Parameter,
    ParameterType,
    Profile,
    ProfileFeature,
    Tag,
    Version,
)


class TestJsonDeserialization(unittest.TestCase):
    """Test cases for JsonDeserialize JSON decoder."""

    def setUp(self):
        """Set up test fixtures."""
        self.decoder = JsonDeserialize()

    def test_deserialize_capability(self):
        """Test deserialization of Capability objects."""
        json_data = {
            "capability": {
                "id": "test_capability",
                "version": "1.0.0",
                "name": "Test Capability",
                "description": "A test capability",
                "requirements": [],
                "metadata": {"path": "test/capability.html"},
            }
        }

        result = json.loads(json.dumps(json_data), cls=JsonDeserialize)

        self.assertIsInstance(result, Capability)
        self.assertEqual(result.id, "test_capability")
        self.assertEqual(result.version, "1.0.0")
        self.assertEqual(result.requirements, [])
        self.assertEqual(result.path, "test/capability")

    def test_deserialize_profile(self):
        """Test deserialization of Profile objects."""
        json_data = {
            "profile": {
                "id": "test_profile",
                "version": "1.0.0",
                "name": "Test Profile",
                "description": "A test profile",
                "features": [],
                "metadata": {"path": "test/profile.html"},
            }
        }

        result = json.loads(json.dumps(json_data), cls=JsonDeserialize)

        self.assertIsInstance(result, Profile)
        self.assertEqual(result.id, "test_profile")
        self.assertEqual(result.version, "1.0.0")
        self.assertEqual(result.display_name, "Test Profile")
        self.assertEqual(result.message, "A test profile")
        self.assertEqual(result.features, [])

    def test_deserialize_profile_optional_feature(self):
        """Test deserialization of optional profile feature references."""
        json_data = {
            "profile": {
                "id": "test_profile",
                "version": "1.0.0",
                "features": [{"feature": "test_feature@1.0.0", "optional": True}],
            }
        }

        result = json.loads(json.dumps(json_data), cls=JsonDeserialize)

        self.assertEqual(result.features, [ProfileFeature(IdVersion("test_feature", Version(1, 0, 0)), optional=True)])
        self.assertTrue(result.features[0].optional)

    def test_deserialize_feature(self):
        """Test deserialization of Feature objects."""
        json_data = {
            "feature": {
                "id": "test_feature",
                "version": "1.0.0",
                "name": "Test Feature",
                "description": "A test feature",
                "custom_data": {"source": "authored"},
                "requirements": ["REQ_001@1.0.0", "REQ_002"],
                "dependencies": ["base_feature@1.0.0"],
                "metadata": {"path": "test/feature.html"},
            }
        }

        result = json.loads(json.dumps(json_data), cls=JsonDeserialize)

        self.assertIsInstance(result, Feature)
        self.assertEqual(result.id, "test_feature")
        self.assertEqual(result.version, "1.0.0")
        self.assertEqual(result.path, "test/feature")
        self.assertEqual(result.requirements, [RequirementRef("REQ_001", "1.0.0"), RequirementRef("REQ_002")])
        self.assertEqual(result.dependencies, [FeatureRef("base_feature", "1.0.0")])
        self.assertEqual(
            result.custom_data,
            {"source": "authored", "name": "Test Feature", "description": "A test feature"},
        )

    def test_deserialize_requirement(self):
        """Test deserialization of Requirement objects."""
        json_data = {
            "code": "TEST_REQ_001",
            "version": "1.0.0",
            "name": "Test Requirement",
            "compatibility": "openusd",
            "tags": "performance",
            "metadata": {"path": "test/requirement.html"},
            "message": "A test requirement",
        }

        result = json.loads(json.dumps(json_data), cls=JsonDeserialize)

        self.assertIsInstance(result, Requirement)
        self.assertEqual(result.code, "TEST_REQ_001")
        self.assertEqual(result.version, "1.0.0")
        self.assertEqual(result.display_name, "Test Requirement")
        self.assertEqual(result.compatibility, Compatibility.OPENUSD.display_name)
        self.assertEqual(result.tags, (Tag.PERFORMANCE.display_name,))
        self.assertEqual(result.message, "A test requirement")
        self.assertEqual(result.path, "test/requirement")

    def test_deserialize_requirement_rejects_null_tag(self):
        """Test deserialization rejects malformed tag lists."""
        json_data = {
            "code": "TEST_REQ_001",
            "version": "1.0.0",
            "tags": ["performance", None],
        }

        result = json.loads(json.dumps(json_data), cls=JsonDeserialize)

        self.assertIsInstance(result, Requirement)
        self.assertEqual(result.tags, (Tag.PERFORMANCE.display_name,))

    def test_deserialize_metadata(self):
        """Test deserialization of Metadata objects."""
        json_data = {"path": "test/metadata.html"}

        result = json.loads(json.dumps(json_data), cls=JsonDeserialize)

        self.assertIsInstance(result, Metadata)

    def test_deserialize_example(self):
        """Test deserialization of Example objects."""
        json_data = {
            "snippet": {"language": "python", "content": "print('Hello, World!')"},
            "name": "A test example",
            "result": "success",
        }

        result = json.loads(json.dumps(json_data), cls=JsonDeserialize)

        self.assertIsInstance(result, Example)
        self.assertEqual(result.snippet.language, ExampleSnippetLanguage.PYTHON)
        self.assertEqual(result.snippet.content, "print('Hello, World!')")
        self.assertEqual(result.display_name, "A test example")
        self.assertEqual(result.result, ExampleResult.SUCCESS)

    def test_deserialize_example_snippet(self):
        """Test deserialization of ExampleSnippet objects."""
        json_data = {"language": "usd", "content": "def Xform 'Root' {}"}

        result = json.loads(json.dumps(json_data), cls=JsonDeserialize)

        self.assertIsInstance(result, ExampleSnippet)
        self.assertEqual(result.language, ExampleSnippetLanguage.USD)
        self.assertEqual(result.content, "def Xform 'Root' {}")

    def test_deserialize_parameter(self):
        """Test deserialization of Parameter objects."""
        json_data = {
            "display_name": "UP_AXIS",
            "type": "enum",
            "assigned_value": "Y",
            "enum_values": ["X", "Y", "Z"],
        }

        result = json.loads(json.dumps(json_data), cls=JsonDeserialize)

        self.assertIsInstance(result, Parameter)
        self.assertEqual(result.display_name, "UP_AXIS")
        self.assertEqual(result.type, ParameterType.ENUM)
        self.assertEqual(result.assigned_value, "Y")
        self.assertEqual(result.enum_values, ["X", "Y", "Z"])

    def test_deserialize_capability_graph_as_plain_dict(self):
        """Test generic deserialization leaves graph JSON untouched."""
        json_data = {
            "schema": "usd-profiles/capability-dag",
            "capabilities": {
                "root": {"kind": "namespace"},
                "root.profile": {
                    "kind": "profile",
                    "predecessors": ["root"],
                },
            },
        }

        result = json.loads(json.dumps(json_data), cls=JsonDeserialize)

        self.assertIsInstance(result, dict)
        self.assertEqual(result, json_data)
