# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import unittest

from usd_profiles_nvidia.api import Requirement
from usd_profiles_nvidia.model import (
    Parameter,
    ParameterType,
)
from usd_profiles_nvidia.store import ParameterStore


class TestParameterStore(unittest.TestCase):
    """Test the ParameterStore's validation and deduplication logic."""

    def test_conflict_different_type(self):
        """Parameters with same name but different type raise an error."""
        req1 = Requirement(
            code="TEST.001", parameters=[Parameter(display_name="AXIS", type=ParameterType.BOOL, assigned_value=True)]
        )
        req2 = Requirement(
            code="TEST.002", parameters=[Parameter(display_name="AXIS", type=ParameterType.INT, assigned_value=1)]
        )

        with self.assertRaises(ValueError) as ctx:
            ParameterStore([req1, req2])

        self.assertIn("AXIS", str(ctx.exception))

    def test_conflict_different_default(self):
        """Parameters with same name but different assigned value raise an error."""
        req1 = Requirement(
            code="TEST.001", parameters=[Parameter(display_name="AXIS", type=ParameterType.INT, assigned_value=1)]
        )
        req2 = Requirement(
            code="TEST.002", parameters=[Parameter(display_name="AXIS", type=ParameterType.INT, assigned_value=2)]
        )

        with self.assertRaises(ValueError):
            ParameterStore([req1, req2])

    def test_conflict_different_enum_values(self):
        """Parameters with same name but different enum values raise an error."""
        req1 = Requirement(
            code="TEST.001",
            parameters=[
                Parameter(display_name="AXIS", type=ParameterType.ENUM, assigned_value="X", enum_values=["X", "Y", "Z"])
            ],
        )
        req2 = Requirement(
            code="TEST.002",
            parameters=[
                Parameter(display_name="AXIS", type=ParameterType.ENUM, assigned_value="X", enum_values=["X", "Y"])
            ],
        )

        with self.assertRaises(ValueError):
            ParameterStore([req1, req2])

    def test_deduplication(self):
        """Identical parameters are deduplicated, different ones are kept."""
        req1 = Requirement(
            code="TEST.001",
            parameters=[
                Parameter(display_name="AXIS", type=ParameterType.INT, assigned_value=1),
                Parameter(display_name="MODE", type=ParameterType.BOOL, assigned_value=True),
            ],
        )
        req2 = Requirement(
            code="TEST.002",
            parameters=[
                Parameter(display_name="AXIS", type=ParameterType.INT, assigned_value=1),  # duplicate
                Parameter(display_name="COUNT", type=ParameterType.INT, assigned_value=0),
            ],
        )

        store = ParameterStore([req1, req2])

        self.assertEqual(len(store), 3)
        self.assertIn("AXIS", store)
        self.assertIn("MODE", store)
        self.assertIn("COUNT", store)

    def test_ordering(self):
        """Parameters are returned in sorted order by name."""
        req = Requirement(
            code="TEST.001",
            parameters=[
                Parameter(display_name="ZEBRA", type=ParameterType.INT, assigned_value=3),
                Parameter(display_name="ALPHA", type=ParameterType.INT, assigned_value=1),
            ],
        )

        store = ParameterStore([req])

        self.assertEqual([p.display_name for p in store], ["ALPHA", "ZEBRA"])

    def test_get(self):
        """Getting a parameter by name."""
        req = Requirement(
            code="TEST.001", parameters=[Parameter(display_name="AXIS", type=ParameterType.INT, assigned_value=1)]
        )

        store = ParameterStore([req])

        self.assertIsNotNone(store.get("AXIS"))
        self.assertIsNone(store.get("NONEXISTENT"))

    def test_empty(self):
        """Empty store works correctly."""
        store = ParameterStore([Requirement(code="TEST.001")])

        self.assertEqual(len(store), 0)
