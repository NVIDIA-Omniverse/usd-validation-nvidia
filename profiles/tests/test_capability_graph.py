# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for usd_profiles_nvidia.graph.CapabilityGraph."""

import json
import os
import tempfile
import unittest

from usd_profiles_nvidia.graph import (
    CapabilityGraph,
    CapabilityGraphDeserializer,
    encode_graph,
)
from usd_profiles_nvidia.model import CapabilityNode

# Test fixture

SAMPLE_DAG = {
    "schema": "usd-profiles/capability-dag",
    "capabilities": {
        "usd": {
            "kind": "namespace",
            "docstring": "Base USD capability",
            "predecessors": [],
        },
        "usd.core": {
            "kind": "capability",
            "domain": "core",
            "docstring": "Core USD validators",
            "predecessors": ["usd"],
            "validators": [
                "usdValidation:CompositionErrorTest",
                "usdValidation:StageMetadataChecker",
                "usdValidation:AttributeTypeMismatch",
            ],
        },
        "usd.geom": {
            "kind": "capability",
            "domain": "geometry",
            "predecessors": ["usd"],
            "validators": [
                "usdGeomValidators:EncapsulationChecker",
                "usdGeomValidators:StageMetadataChecker",
            ],
        },
        "usd.physics": {
            "kind": "capability",
            "domain": "physics",
            "predecessors": ["usd"],
            "validators": [
                "usdPhysicsValidators:RigidBodyChecker",
                "usdPhysicsValidators:ColliderChecker",
            ],
        },
        "usd.core.v25_05": {
            "kind": "profile",
            "predecessors": ["usd.core", "usd.geom", "usd.physics"],
        },
        "com.nvidia.simready": {
            "kind": "namespace",
            "predecessors": ["usd"],
        },
        "com.nvidia.simready.geom": {
            "kind": "feature",
            "domain": "geometry",
            "predecessors": ["com.nvidia.simready", "usd.geom"],
            "validators": [
                "simready:VG.MESH.001",
                "simready:VG.014",
            ],
        },
        "com.nvidia.simready.physics": {
            "kind": "feature",
            "domain": "physics",
            "predecessors": ["com.nvidia.simready", "usd.physics"],
            "validators": [
                "simready:RB.003",
            ],
        },
        "com.nvidia.simready.prop_neutral": {
            "kind": "profile",
            "predecessors": [
                "com.nvidia.simready.geom",
                "com.nvidia.simready.physics",
            ],
        },
    },
}


class TestCapabilityGraphLoading(unittest.TestCase):
    """Tests for loading capabilities."""

    def test_load_from_dict(self):
        graph = CapabilityGraph.load_from_dict(SAMPLE_DAG)
        self.assertEqual(len(graph), 9)

    def test_load_from_dict_builds_typed_nodes(self):
        graph = CapabilityGraph.load_from_dict(SAMPLE_DAG)

        self.assertIsInstance(graph.nodes["usd"], CapabilityNode)
        self.assertEqual(graph.nodes["usd"].kind, "namespace")

    def test_load_from_json_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(SAMPLE_DAG, f)
            path = f.name

        try:
            graph = CapabilityGraph.load_from_json(path)
            self.assertEqual(len(graph), 9)
        finally:
            os.unlink(path)

    def test_deserializer_loads_graph(self):
        graph = json.loads(json.dumps(SAMPLE_DAG), cls=CapabilityGraphDeserializer)

        self.assertIsInstance(graph, CapabilityGraph)
        self.assertIn("usd", graph)
        self.assertTrue(graph.is_profile("usd.core.v25_05"))

    def test_deserializer_ignores_non_graph_capabilities_dict(self):
        data = {"name": "permissions", "capabilities": {"read": True}}

        decoded = json.loads(json.dumps(data), cls=CapabilityGraphDeserializer)

        self.assertEqual(decoded, data)

    def test_load_no_schema_is_ok(self):
        """Missing schema field is accepted (backward compat)."""
        data = {"capabilities": {"foo": {"kind": "namespace"}}}
        graph = CapabilityGraph.load_from_dict(data)
        self.assertIn("foo", graph)


class TestCapabilityGraphQueries(unittest.TestCase):
    """Tests for query methods."""

    def setUp(self):
        self.graph = CapabilityGraph.load_from_dict(SAMPLE_DAG)

    def test_is_capability(self):
        self.assertTrue(self.graph.is_capability("usd"))
        self.assertTrue(self.graph.is_capability("com.nvidia.simready.geom"))
        self.assertFalse(self.graph.is_capability("nonexistent"))

    def test_is_profile(self):
        self.assertTrue(self.graph.is_profile("usd.core.v25_05"))
        self.assertTrue(self.graph.is_profile("com.nvidia.simready.prop_neutral"))
        self.assertFalse(self.graph.is_profile("usd"))
        self.assertFalse(self.graph.is_profile("com.nvidia.simready.geom"))

    def test_get_kind(self):
        self.assertEqual(self.graph.get_kind("usd"), "namespace")
        self.assertEqual(self.graph.get_kind("usd.core"), "capability")
        self.assertEqual(self.graph.get_kind("com.nvidia.simready.geom"), "feature")
        self.assertEqual(self.graph.get_kind("usd.core.v25_05"), "profile")
        self.assertEqual(self.graph.get_kind("nonexistent"), "")

    def test_get_predecessors(self):
        preds = self.graph.get_predecessors("usd.core")
        self.assertEqual(preds, ["usd"])

        preds = self.graph.get_predecessors("com.nvidia.simready.geom")
        self.assertIn("com.nvidia.simready", preds)
        self.assertIn("usd.geom", preds)

    def test_get_transitive_predecessors(self):
        trans = self.graph.get_transitive_predecessors("com.nvidia.simready.prop_neutral")
        self.assertIn("com.nvidia.simready.geom", trans)
        self.assertIn("com.nvidia.simready.physics", trans)
        self.assertIn("com.nvidia.simready", trans)
        self.assertIn("usd.geom", trans)
        self.assertIn("usd.physics", trans)
        self.assertIn("usd", trans)

    def test_get_validators(self):
        vals = self.graph.get_validators("usd.core")
        self.assertEqual(len(vals), 3)
        self.assertIn("usdValidation:CompositionErrorTest", vals)

    def test_get_validators_empty(self):
        vals = self.graph.get_validators("usd")
        self.assertEqual(vals, [])

    def test_get_all_validators_for_profile(self):
        vals = self.graph.get_all_validators_for_capability("com.nvidia.simready.prop_neutral")
        # SimReady: VG.MESH.001, VG.014, RB.003 = 3
        # Pixar bridge: 2 geom + 2 physics = 4
        # Total = 7
        self.assertEqual(len(vals), 7)
        self.assertIn("simready:VG.MESH.001", vals)
        self.assertIn("usdGeomValidators:EncapsulationChecker", vals)
        self.assertIn("usdPhysicsValidators:RigidBodyChecker", vals)

    def test_get_all_validators_no_duplicates(self):
        vals = self.graph.get_all_validators_for_capability("com.nvidia.simready.prop_neutral")
        self.assertEqual(len(vals), len(set(vals)))

    def test_get_all_capabilities(self):
        caps = self.graph.get_all_capabilities()
        self.assertEqual(len(caps), 9)
        self.assertEqual(caps, sorted(caps))

    def test_get_all_profiles(self):
        profiles = self.graph.get_all_profiles()
        self.assertEqual(len(profiles), 2)
        self.assertIn("usd.core.v25_05", profiles)
        self.assertIn("com.nvidia.simready.prop_neutral", profiles)


class TestCapabilityGraphFiltering(unittest.TestCase):
    """Tests for namespace filtering."""

    def setUp(self):
        self.graph = CapabilityGraph.load_from_dict(SAMPLE_DAG)

    def test_filter_simready(self):
        filtered = self.graph.filter_by_namespace("com.nvidia.simready")
        for cap in filtered:
            self.assertTrue(cap.startswith("com.nvidia.simready"))
        self.assertNotIn("usd.geom", filtered)

    def test_filter_usd(self):
        filtered = self.graph.filter_by_namespace("usd")
        for cap in filtered:
            self.assertTrue(cap.startswith("usd"))
        self.assertNotIn("com.nvidia.simready", filtered)

    def test_filter_with_predecessors(self):
        filtered = self.graph.filter_by_namespace("com.nvidia.simready", include_predecessors=True)
        self.assertIn("usd.geom", filtered)
        self.assertIn("usd.physics", filtered)
        self.assertIn("usd", filtered)

    def test_filter_nonexistent(self):
        filtered = self.graph.filter_by_namespace("com.example.nope")
        self.assertEqual(filtered, [])


class TestCapabilityGraphMerge(unittest.TestCase):
    """Tests for merging graphs."""

    def test_merge_disjoint(self):
        g1 = CapabilityGraph.load_from_dict({"capabilities": {"a": {"kind": "namespace"}}})
        g2 = CapabilityGraph.load_from_dict({"capabilities": {"b": {"kind": "namespace"}}})
        g1.merge(g2)
        self.assertEqual(len(g1), 2)
        self.assertIn("a", g1)
        self.assertIn("b", g1)

    def test_merge_conflict_keeps_first(self):
        g1 = CapabilityGraph.load_from_dict({"capabilities": {"a": {"kind": "namespace", "docstring": "first"}}})
        g2 = CapabilityGraph.load_from_dict({"capabilities": {"a": {"kind": "namespace", "docstring": "second"}}})
        with self.assertLogs("usd_profiles_nvidia.graph._graph", level="WARNING"):
            g1.merge(g2)
        self.assertEqual(g1.get_docstring("a"), "first")


class TestCapabilityGraphSerialization(unittest.TestCase):
    """Tests for encode_graph / to_json round-trip."""

    def test_round_trip_dict(self):
        g1 = CapabilityGraph.load_from_dict(SAMPLE_DAG)

        data = encode_graph(g1)
        g2 = CapabilityGraph.load_from_dict(data)

        self.assertEqual(len(g1), len(g2))
        self.assertEqual(
            g1.get_all_validators_for_capability("com.nvidia.simready.prop_neutral"),
            g2.get_all_validators_for_capability("com.nvidia.simready.prop_neutral"),
        )

    def test_round_trip_json_file(self):
        g1 = CapabilityGraph.load_from_dict(SAMPLE_DAG)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name

        try:
            g1.to_json(path)
            g2 = CapabilityGraph.load_from_json(path)
            self.assertEqual(len(g1), len(g2))
        finally:
            os.unlink(path)

    def test_encode_graph_schema_version(self):
        graph = CapabilityGraph.load_from_dict(SAMPLE_DAG)
        data = encode_graph(graph)
        self.assertEqual(data["schema"], "usd-profiles/capability-dag")


class TestCapabilityGraphContainer(unittest.TestCase):
    """Tests for __contains__."""

    def test_contains(self):
        graph = CapabilityGraph.load_from_dict(SAMPLE_DAG)
        self.assertIn("usd", graph)
        self.assertNotIn("nonexistent", graph)
