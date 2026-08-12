# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import unittest
from pathlib import Path

from usd_profiles_nvidia.markdown import RequirementsParser
from usd_profiles_nvidia.model import Compatibility, Tag


class TestRequirementsParser(unittest.TestCase):

    def test_parse_ok(self):
        base_dir = Path(__file__).parent / "resources" / "simple-spec" / "capabilities" / "geometry"
        parser = RequirementsParser(root_dir=str(base_dir), paths=[str(base_dir / "requirements")])
        requirements = parser.parse()

        self.assertGreaterEqual(len(requirements), 1)

        req = next((r for r in requirements if r.code == "VG.RTX.002"), None)
        self.assertIsNotNone(req, "VG.RTX.002 requirement should exist")
        self.assertEqual(req.version, "1.0.0")
        self.assertEqual(req.display_name, "usdgeom-mesh-count")
        self.assertEqual(req.message, "Use appropriate mesh count for scene.")
        self.assertEqual(req.compatibility, Compatibility.RTX.display_name)
        self.assertEqual(req.validator, "{oav-validator-latest-link}`vg-rtx-002`")
        self.assertEqual(req.tags, (Tag.PERFORMANCE.display_name,))
        self.assertIsInstance(req.parameters, tuple)
        self.assertEqual(len(req.parameters), 0)

    def test_parse_parameters_ok(self):
        base_dir = Path(__file__).parent / "resources" / "param-test-spec"
        capability_dir = base_dir / "capabilities" / "test"
        parser = RequirementsParser(root_dir=str(base_dir), paths=[str(capability_dir / "requirements")])
        requirements = parser.parse()

        # Test requirement with multiple parameters (VG.RTX.003)
        req = next((r for r in requirements if r.code == "VG.RTX.003"), None)
        self.assertIsNotNone(req)
        self.assertEqual(req.version, "1.0.0")
        self.assertEqual(req.display_name, "usdgeom-param-test")
        self.assertIsInstance(req.parameters, tuple)
        self.assertEqual(len(req.parameters), 3)

        params = {p.display_name: p for p in req.parameters}

        self.assertEqual(params["UP_AXIS"].type, "enum")
        self.assertEqual(params["UP_AXIS"].assigned_value, "X")
        self.assertCountEqual(params["UP_AXIS"].enum_values, ["X", "Y", "Z"])

        self.assertEqual(params["NESTING_LEVEL"].type, "int")
        self.assertEqual(params["NESTING_LEVEL"].assigned_value, 0)

        self.assertEqual(params["ENABLED"].type, "bool")
        self.assertEqual(params["ENABLED"].assigned_value, False)

        # Test requirement with single enum value (VG.RTX.004)
        req = next((r for r in requirements if r.code == "VG.RTX.004"), None)
        self.assertIsNotNone(req, "VG.RTX.004 requirement should exist")
        self.assertEqual(len(req.parameters), 1)
        self.assertEqual(req.parameters[0].display_name, "MODE")
        self.assertEqual(req.parameters[0].type, "enum")
        self.assertEqual(req.parameters[0].assigned_value, "A")
        self.assertCountEqual(req.parameters[0].enum_values, ["A"])

    def test_invalid_enum_default_logs_error_ok(self):
        base_dir = Path(__file__).parent / "resources" / "invalid-specs"
        parser = RequirementsParser(root_dir=str(base_dir), paths=[str(base_dir / "requirements")])

        with self.assertLogs("usd_profiles_nvidia.markdown._requirements", level="WARNING") as cm:
            parser.parse()
        self.assertRegex(cm.output[0], r"Assigned value.*'D'.*not within declared enum values")

    def test_multiple_parameter_tables_logs_error_ok(self):
        base_dir = Path(__file__).parent / "resources" / "multi-table-spec"
        parser = RequirementsParser(root_dir=str(base_dir), paths=[str(base_dir / "requirements")])

        with self.assertLogs("usd_profiles_nvidia.markdown._requirements", level="WARNING") as cm:
            parser.parse()
        self.assertRegex(cm.output[0], r"Multiple parameter tables.*Expected 1 table, found 2")
