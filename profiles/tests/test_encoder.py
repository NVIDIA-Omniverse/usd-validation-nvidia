# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import json
import unittest

from usd_profiles_nvidia.api import Capability, Feature, FeatureRef, Requirement, RequirementRef
from usd_profiles_nvidia.graph import CapabilityGraph
from usd_profiles_nvidia.json import (
    JsonDeserialize,
    JsonSerialize,
)
from usd_profiles_nvidia.model import (
    BuildCapabilityGraph,
    CapabilityNode,
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


class TestJsonSerialization(unittest.TestCase):
    """Test cases for JsonSerialize JSON encoder."""

    def setUp(self):
        """Set up test fixtures."""
        self.encoder = JsonSerialize()
        self.decoder = JsonDeserialize()

    def test_serialize_requirement(self):
        """Test serialization of Requirement objects."""
        requirement = Requirement(
            code="TEST_REQ_001",
            version="1.0.0",
            display_name="Test Requirement",
            message="A test requirement for unit testing",
            path="capabilities/test-requirement",
            compatibility="high",
            tags=(Tag.PERFORMANCE.display_name, Tag.CORRECTNESS.display_name),
        )

        result = json.loads(json.dumps(requirement, cls=JsonSerialize))

        expected = {
            "code": "TEST_REQ_001",
            "version": "1.0.0",
            "name": "Test Requirement",
            "compatibility": "high",
            "tags": [Tag.PERFORMANCE.display_name, Tag.CORRECTNESS.display_name],
            "validator": None,
            "parameters": [],
            "metadata": {
                "path": "capabilities/test-requirement.html",
                "internal_path": "capabilities/test-requirement.md",
            },
            "message": "A test requirement for unit testing",
            "examples": [],
        }

        self.assertEqual(result, expected)

    def test_serialize_requirement_with_none_values(self):
        """Test serialization of Requirement with None values."""
        requirement = Requirement(code="TEST_REQ_002", display_name="Test Requirement 2")

        result = json.loads(json.dumps(requirement, cls=JsonSerialize))

        expected = {
            "code": "TEST_REQ_002",
            "version": None,
            "name": "Test Requirement 2",
            "compatibility": None,
            "tags": None,
            "validator": None,
            "parameters": [],
            "metadata": None,
            "message": None,
            "examples": [],
        }

        self.assertEqual(result, expected)

    def test_serialize_capability(self):
        """Test serialization of Capability objects."""
        metadata = Metadata("capabilities/test-capability.md")
        requirement = Requirement(code="REQ_001", display_name="Test Req")

        capability = Capability(
            id="test_capability",
            version="1.0.0",
            path=metadata.path,
            requirements=[requirement],
        )

        result = json.loads(json.dumps(capability, cls=JsonSerialize))

        self.assertIn("capability", result)
        cap_data = result["capability"]
        self.assertEqual(cap_data["id"], "test_capability")
        self.assertEqual(cap_data["version"], "1.0.0")
        self.assertNotIn("name", cap_data)
        self.assertNotIn("description", cap_data)
        self.assertEqual(len(cap_data["requirements"]), 1)
        self.assertIn("metadata", cap_data)

    def test_serialize_profile(self):
        """Test serialization of Profile objects."""
        metadata = Metadata("profiles/test-profile.md")

        profile = Profile(
            id="test_profile",
            version="1.0.0",
            display_name="Test Profile",
            message="A test profile",
            metadata=metadata,
            features=[ProfileFeature(IdVersion("test_feature", Version(1, 0, 0)))],
        )

        result = json.loads(json.dumps(profile, cls=JsonSerialize))

        self.assertIn("profile", result)
        prof_data = result["profile"]
        self.assertEqual(prof_data["id"], "test_profile")
        self.assertEqual(prof_data["version"], "1.0.0")
        self.assertEqual(prof_data["name"], "Test Profile")
        self.assertEqual(prof_data["description"], "A test profile")
        self.assertEqual(prof_data["features"], [{"feature": "test_feature@1.0.0", "optional": False}])

    def test_serialize_profile_optional_feature(self):
        """Test serialization of optional profile feature references."""
        profile = Profile(
            id="test_profile",
            version="1.0.0",
            features=[ProfileFeature(IdVersion("test_feature", Version(1, 0, 0)), optional=True)],
        )

        result = json.loads(json.dumps(profile, cls=JsonSerialize))

        self.assertEqual(
            result["profile"]["features"],
            [{"feature": "test_feature@1.0.0", "optional": True}],
        )

    def test_serialize_feature(self):
        """Test serialization of Feature objects."""
        metadata = Metadata("features/test-feature.md")

        feature = Feature(
            id="test_feature",
            version="1.0.0",
            path=metadata.path,
            requirements=[RequirementRef("FEAT_REQ_001")],
            dependencies=[FeatureRef("base_feature", "1.0.0")],
            custom_data={"display_name": "Test Feature"},
        )

        result = json.loads(json.dumps(feature, cls=JsonSerialize))

        self.assertIn("feature", result)
        feat_data = result["feature"]
        self.assertEqual(feat_data["id"], "test_feature")
        self.assertEqual(feat_data["version"], "1.0.0")
        self.assertNotIn("name", feat_data)
        self.assertNotIn("description", feat_data)
        self.assertEqual(
            feat_data["metadata"],
            {"path": "features/test-feature.html", "internal_path": "features/test-feature.md"},
        )
        self.assertEqual(feat_data["requirements"], ["FEAT_REQ_001"])
        self.assertEqual(feat_data["dependencies"], ["base_feature@1.0.0"])
        self.assertEqual(feat_data["display_name"], "Test Feature")

    def test_serialize_metadata(self):
        """Test serialization of Metadata objects."""
        metadata = Metadata("test/example.md")

        result = json.loads(json.dumps(metadata, cls=JsonSerialize))

        expected = {"path": "test/example.html", "internal_path": "test/example.md"}

        self.assertEqual(result, expected)

    def test_serialize_parameter(self):
        """Test serialization of Parameter objects."""
        param = Parameter(display_name="AXIS", type=ParameterType.ENUM, assigned_value="X", enum_values=["X", "Y", "Z"])
        result = json.loads(json.dumps(param, cls=JsonSerialize))

        expected = {
            "display_name": "AXIS",
            "type": "enum",
            "assigned_value": "X",
            "enum_values": ["X", "Y", "Z"],
        }

        self.assertEqual(result, expected)

    def test_serialize_example(self):
        """Test serialization of Example objects."""
        example = Example(
            snippet=ExampleSnippet(language=ExampleSnippetLanguage.PYTHON, content="print('Hello, World!')"),
            display_name="A test example",
            result=ExampleResult.SUCCESS,
        )
        result = json.loads(json.dumps(example, cls=JsonSerialize))

        expected = {
            "snippet": {
                "language": "python",
                "content": "print('Hello, World!')",
            },
            "name": "A test example",
            "result": "success",
        }
        self.assertEqual(result, expected)

    def test_serialize_example_snippet(self):
        """Test serialization of ExampleSnippet objects."""
        snippet = ExampleSnippet(language=ExampleSnippetLanguage.USD, content="def Xform 'Root' {}")
        result = json.loads(json.dumps(snippet, cls=JsonSerialize))

        expected = {"language": "usd", "content": "def Xform 'Root' {}"}
        self.assertEqual(result, expected)

    def test_serialize_version(self):
        """Test serialization of Version objects."""
        version = Version(2, 5, 1)
        result = json.loads(json.dumps(version, cls=JsonSerialize))

        self.assertEqual(result, "2.5.1")

    def test_serialize_id_version(self):
        """Test serialization of IdVersion objects."""
        # With version
        id_version = IdVersion("REQ_001", Version(1, 0, 0))
        result = json.loads(json.dumps(id_version, cls=JsonSerialize))
        self.assertEqual(result, "REQ_001@1.0.0")

        # Without version
        id_version_no_ver = IdVersion("REQ_002", None)
        result_no_ver = json.loads(json.dumps(id_version_no_ver, cls=JsonSerialize))
        self.assertEqual(result_no_ver, "REQ_002")

    def test_serialize_build_capability_graph(self):
        """Test serialization of build graph objects to capabilities.json shape."""
        graph = BuildCapabilityGraph()
        graph.add_node(CapabilityNode(id="root", kind="namespace", docstring="Root"))
        graph.add_node(
            CapabilityNode(
                id="root.geom",
                kind="capability",
                predecessors=["root"],
                requirements={
                    "VG.001": Requirement(
                        code="VG.001",
                        display_name="mesh-topology",
                        validator="oav:vg-001",
                        tags=(Tag.CORRECTNESS.display_name,),
                        parameters=(Parameter(display_name="max_faces", type=ParameterType.INT, assigned_value=128),),
                        examples=(
                            Example(
                                snippet=ExampleSnippet(
                                    language=ExampleSnippetLanguage.USD,
                                    content='def Mesh "bad" {}',
                                ),
                                display_name="Bad mesh",
                                result=ExampleResult.FAILURE,
                            ),
                        ),
                    )
                },
            )
        )

        result = json.loads(json.dumps(graph, cls=JsonSerialize))

        self.assertEqual(result["schema"], "usd-profiles/capability-dag")
        self.assertEqual(result["capabilities"]["root"]["kind"], "namespace")
        self.assertEqual(result["capabilities"]["root.geom"]["predecessors"], ["root"])
        self.assertEqual(
            result["capabilities"]["root.geom"]["requirements"]["VG.001"]["name"],
            "mesh-topology",
        )
        self.assertEqual(
            result["capabilities"]["root.geom"]["requirements"]["VG.001"]["validator"],
            "oav:vg-001",
        )
        self.assertEqual(
            result["capabilities"]["root.geom"]["requirements"]["VG.001"]["parameters"][0]["display_name"],
            "max_faces",
        )
        self.assertEqual(
            result["capabilities"]["root.geom"]["requirements"]["VG.001"]["examples"][0]["result"],
            "failure",
        )

    def test_serialize_capability_graph(self):
        """Test serialization of runtime graph objects to capabilities.json shape."""
        graph = CapabilityGraph.load_from_dict(
            {
                "capabilities": {
                    "root": {"kind": "namespace"},
                    "root.geom": {
                        "kind": "capability",
                        "predecessors": ["root"],
                    },
                },
            }
        )

        result = json.loads(json.dumps(graph, cls=JsonSerialize))

        self.assertEqual(result["schema"], "usd-profiles/capability-dag")
        self.assertEqual(result["capabilities"]["root"]["kind"], "namespace")
        self.assertEqual(result["capabilities"]["root.geom"]["predecessors"], ["root"])
