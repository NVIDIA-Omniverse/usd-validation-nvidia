# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for enriched requirements in capabilities.json DAG."""

import copy
import os
import tempfile
import unittest

from usd_profiles_nvidia.api import Requirement
from usd_profiles_nvidia.graph import CapabilityGraph, encode_graph
from usd_profiles_nvidia.model import (
    Example,
    ExampleResult,
    ExampleSnippet,
    ExampleSnippetLanguage,
    Parameter,
    ParameterType,
)

# Fixtures

SAMPLE_DATA = {
    "schema": "usd-profiles/capability-dag",
    "capabilities": {
        "root": {
            "kind": "namespace",
            "predecessors": [],
            "docstring": "Root namespace",
        },
        "root.geom": {
            "kind": "capability",
            "predecessors": ["root"],
            "validators": ["root:VG.014", "root:VG.027"],
            "docstring": "Geometry checks",
            "domain": "geometry",
            "requirements": {
                "VG.014": {
                    "display_name": "mesh-topology",
                    "message": "Mesh topology must be valid",
                    "version": "1.0.0",
                    "path": "geometry/requirements/mesh-topology.html",
                    "compatibility": "core-usd",
                    "validator": "simready:VG.014",
                    "tags": ["correctness"],
                    "parameters": [
                        {
                            "display_name": "max_faces",
                            "type": "int",
                            "assigned_value": 128,
                        }
                    ],
                    "examples": [
                        {
                            "name": "Invalid mesh topology",
                            "result": "failure",
                            "snippet": {
                                "language": "usd",
                                "filename": "bad_topo.usda",
                                "content": '#usda 1.0\ndef Mesh "bad" {}',
                            },
                        }
                    ],
                },
                "VG.027": {
                    "display_name": "normals-exist",
                    "message": "All non-subdivided meshes must have normals.",
                    "version": "1.0.0",
                    "tags": ["correctness"],
                },
            },
        },
        "root.profile.basic": {
            "kind": "profile",
            "predecessors": ["root.geom"],
            "docstring": "Basic profile",
        },
    },
}

# Minimal data without requirements, e.g. a namespace-only DAG.
MINIMAL_DATA = {
    "schema": "usd-profiles/capability-dag",
    "capabilities": {
        "root": {
            "kind": "namespace",
            "predecessors": [],
            "docstring": "Root namespace",
        },
        "root.geom": {
            "kind": "capability",
            "predecessors": ["root"],
            "validators": ["root:VG.014", "root:VG.027"],
            "docstring": "Geometry checks",
            "domain": "geometry",
        },
    },
}


# Tests


class TestGraphRequirement(unittest.TestCase):
    """Test graph requirement DTOs."""

    def test_create_minimal(self):
        r = Requirement(code="VG.001")
        self.assertEqual(r.code, "VG.001")
        self.assertIsNone(r.display_name)
        self.assertEqual(r.tags, ())
        self.assertEqual(r.parameters, ())

    def test_create_full(self):
        parameter = Parameter(display_name="max_faces", type=ParameterType.INT)
        example = Example(
            snippet=ExampleSnippet(language=ExampleSnippetLanguage.USD, content='def Mesh "bad" {}'),
            display_name="Bad mesh",
            result=ExampleResult.FAILURE,
        )
        r = Requirement(
            code="VG.014",
            display_name="mesh-topology",
            message="Mesh topology must be valid",
            version="1.0.0",
            path="geometry/requirements/mesh-topology.html",
            compatibility="core-usd",
            validator="simready:VG.014",
            tags=("correctness",),
            parameters=(parameter,),
            examples=(example,),
        )
        self.assertEqual(r.display_name, "mesh-topology")
        self.assertEqual(r.validator, "simready:VG.014")
        self.assertEqual(r.tags, ("correctness",))
        self.assertIs(r.parameters[0], parameter)
        self.assertIs(r.examples[0], example)
        self.assertEqual(len(r.parameters), 1)
        self.assertEqual(len(r.examples), 1)

    def test_frozen(self):
        r = Requirement(code="VG.001")
        with self.assertRaises(AttributeError):
            r.code = "VG.002"


class TestRequirementsLoading(unittest.TestCase):
    """Requirements load correctly from capabilities.json."""

    def setUp(self):
        self.g = CapabilityGraph.load_from_dict(SAMPLE_DATA)

    def test_node_count(self):
        self.assertEqual(len(self.g), 3)

    def test_requirements_on_node(self):
        reqs = self.g.get_requirements("root.geom")
        self.assertEqual(len(reqs), 2)
        codes = {r.code for r in reqs}
        self.assertEqual(codes, {"VG.014", "VG.027"})

    def test_get_requirement_by_code(self):
        r = self.g.get_requirement("VG.014")
        self.assertIsNotNone(r)
        self.assertEqual(r.display_name, "mesh-topology")
        self.assertEqual(r.message, "Mesh topology must be valid")
        self.assertEqual(r.version, "1.0.0")
        self.assertEqual(r.compatibility, "core-usd")
        self.assertEqual(r.validator, "simready:VG.014")
        self.assertEqual(r.tags, ("correctness",))
        self.assertEqual(len(r.parameters), 1)
        self.assertIsInstance(r.parameters[0], Parameter)
        self.assertEqual(r.parameters[0].display_name, "max_faces")
        self.assertEqual(r.parameters[0].type, ParameterType.INT)
        self.assertEqual(r.parameters[0].assigned_value, 128)
        self.assertEqual(len(r.examples), 1)
        self.assertIsInstance(r.examples[0], Example)
        self.assertEqual(r.examples[0].display_name, "Invalid mesh topology")
        self.assertEqual(r.examples[0].result, ExampleResult.FAILURE)
        self.assertEqual(r.examples[0].snippet.language, ExampleSnippetLanguage.USD)

    def test_get_requirement_not_found(self):
        self.assertIsNone(self.g.get_requirement("NONEXISTENT.001"))

    def test_get_all_requirements(self):
        all_reqs = self.g.get_all_requirements()
        self.assertEqual(len(all_reqs), 2)
        # Should be sorted by code.
        self.assertEqual(all_reqs[0].code, "VG.014")
        self.assertEqual(all_reqs[1].code, "VG.027")

    def test_requirements_on_namespace_empty(self):
        self.assertEqual(self.g.get_requirements("root"), [])

    def test_requirements_on_profile_empty(self):
        self.assertEqual(self.g.get_requirements("root.profile.basic"), [])

    def test_minimal_data_has_no_requirements(self):
        """Nodes without a requirements block still load correctly."""
        g = CapabilityGraph.load_from_dict(MINIMAL_DATA)
        self.assertEqual(len(g), 2)
        self.assertEqual(g.get_requirements("root.geom"), [])
        self.assertEqual(g.get_all_requirements(), [])

    def test_missing_example_fields_raise_contextual_error(self):
        cases = {
            "snippet": lambda example: example.pop("snippet"),
            "result": lambda example: example.pop("result"),
            "language": lambda example: example["snippet"].pop("language"),
        }
        for field, mutate in cases.items():
            with self.subTest(field=field):
                data = copy.deepcopy(SAMPLE_DATA)
                example = data["capabilities"]["root.geom"]["requirements"]["VG.014"]["examples"][0]
                mutate(example)

                with self.assertRaises(ValueError) as cm:
                    CapabilityGraph.load_from_dict(data)
                message = str(cm.exception)
                self.assertIn(field, message)
                self.assertIn("root.geom", message)
                self.assertIn("VG.014", message)


class TestRequirementsSerialization(unittest.TestCase):
    """Requirements round-trip through JSON."""

    def test_roundtrip(self):
        g = CapabilityGraph.load_from_dict(SAMPLE_DATA)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            path = f.name
        g.to_json(path)

        g2 = CapabilityGraph.load_from_json(path)
        os.unlink(path)

        # Verify requirements survived.
        r = g2.get_requirement("VG.014")
        self.assertIsNotNone(r)
        self.assertEqual(r.display_name, "mesh-topology")
        self.assertEqual(r.validator, "simready:VG.014")
        self.assertEqual(r.tags, ("correctness",))
        self.assertEqual(len(r.examples), 1)

    def test_schema_version(self):
        g = CapabilityGraph.load_from_dict(SAMPLE_DATA)
        d = encode_graph(g)
        self.assertEqual(d["schema"], "usd-profiles/capability-dag")

    def test_requirements_in_dict(self):
        g = CapabilityGraph.load_from_dict(SAMPLE_DATA)
        d = encode_graph(g)
        geom = d["capabilities"]["root.geom"]
        self.assertIn("requirements", geom)
        self.assertIn("VG.014", geom["requirements"])
        self.assertEqual(geom["requirements"]["VG.014"]["name"], "mesh-topology")
        self.assertEqual(geom["requirements"]["VG.014"]["validator"], "simready:VG.014")


class TestOAVProtocolCompat(unittest.TestCase):
    """Graph requirements should satisfy OAV's Requirement protocol fields."""

    def test_has_protocol_fields(self):
        r = Requirement(
            code="VG.014",
            display_name="mesh-topology",
            message="Mesh topology must be valid",
            version="1.0.0",
            path="geometry/requirements/mesh-topology.html",
            compatibility="core-usd",
            validator="simready:VG.014",
            tags=("correctness",),
            parameters=(),
            examples=(),
        )
        # These are the fields OAV's Requirement protocol requires:
        self.assertTrue(hasattr(r, "code"))
        self.assertTrue(hasattr(r, "display_name"))
        self.assertTrue(hasattr(r, "message"))
        self.assertTrue(hasattr(r, "path"))
        self.assertTrue(hasattr(r, "compatibility"))
        self.assertTrue(hasattr(r, "validator"))
        self.assertTrue(hasattr(r, "tags"))
        self.assertTrue(hasattr(r, "version"))
        self.assertTrue(hasattr(r, "parameters"))
        self.assertTrue(hasattr(r, "examples"))
