# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import unittest
from dataclasses import dataclass

from nvidia_usd_validation import Parameter, ParameterMapping, ParameterType, UserParameter


@dataclass(frozen=True)
class MyParameter:
    """Example dataclass parameter that conforms to the Parameter protocol."""

    display_name: str
    type: ParameterType
    assigned_value: int | bool | float | str | None = None
    enum_values: tuple[str, ...] | None = None


# Create some test parameter instances
UP_AXIS = MyParameter(display_name="UP_AXIS", type=ParameterType.ENUM, assigned_value="Y", enum_values=("X", "Y", "Z"))
TOLERANCE = MyParameter(display_name="TOLERANCE", type=ParameterType.FLOAT, assigned_value=1e-6)
ENABLE_WARNINGS = MyParameter(display_name="ENABLE_WARNINGS", type=ParameterType.BOOL, assigned_value=True)
MAX_ITERATIONS = MyParameter(display_name="MAX_ITERATIONS", type=ParameterType.INT, assigned_value=100)


class ParameterProtocolTests(unittest.TestCase):
    """Tests for the Parameter protocol."""

    def test_int_parameter(self):
        """Test a parameter with int type."""
        param = MyParameter(display_name="max_iterations", type=ParameterType.INT, assigned_value=100)

        self.assertIsInstance(param, Parameter)
        self.assertEqual(param.display_name, "max_iterations")
        self.assertEqual(param.type, ParameterType.INT)
        self.assertEqual(param.assigned_value, 100)

    def test_enum_parameter(self):
        """Test a parameter with enum type."""
        param = MyParameter(
            display_name="color", type=ParameterType.ENUM, assigned_value="red", enum_values=("red", "green", "blue")
        )

        self.assertIsInstance(param, Parameter)
        self.assertEqual(param.display_name, "color")
        self.assertEqual(param.type, ParameterType.ENUM)
        self.assertEqual(param.assigned_value, "red")
        self.assertEqual(param.enum_values, ("red", "green", "blue"))

    def test_bool_parameter(self):
        """Test a parameter with bool type."""
        param = MyParameter(display_name="enabled", type=ParameterType.BOOL, assigned_value=True)

        self.assertIsInstance(param, Parameter)
        self.assertEqual(param.display_name, "enabled")
        self.assertEqual(param.type, ParameterType.BOOL)
        self.assertEqual(param.assigned_value, True)

    def test_float_parameter(self):
        """Test a parameter with float type."""
        param = MyParameter(display_name="tolerance", type=ParameterType.FLOAT, assigned_value=1e-6)

        self.assertIsInstance(param, Parameter)
        self.assertEqual(param.display_name, "tolerance")
        self.assertEqual(param.type, ParameterType.FLOAT)
        self.assertEqual(param.assigned_value, 1e-6)


class ParameterMappingTests(unittest.TestCase):
    """Tests for ParameterMapping custom behavior (inherits from UserDict)."""

    def test_init_ok(self):
        params = ParameterMapping((UP_AXIS, TOLERANCE, ENABLE_WARNINGS))

        self.assertEqual(len(params), 3)
        self.assertEqual(params["UP_AXIS"], UP_AXIS)
        self.assertEqual(params["TOLERANCE"], TOLERANCE)
        self.assertEqual(params["ENABLE_WARNINGS"], ENABLE_WARNINGS)

    def test_add_ok(self):
        params = ParameterMapping()
        params.add(UP_AXIS)
        params.add(TOLERANCE)

        self.assertEqual(len(params), 2)
        self.assertEqual(params["UP_AXIS"], UP_AXIS)
        self.assertEqual(params["TOLERANCE"], TOLERANCE)

    def test_iter_ok(self):
        params = ParameterMapping((UP_AXIS, TOLERANCE))

        param_list = list(params)
        self.assertEqual(param_list, [UP_AXIS, TOLERANCE])

    def test_contains_ok(self):
        params = ParameterMapping((UP_AXIS,))

        self.assertIn("UP_AXIS", params)  # String name
        self.assertIn(UP_AXIS, params)  # Parameter object
        self.assertNotIn(TOLERANCE, params)

    def test_add_type_error(self):
        params = ParameterMapping()

        with self.assertRaises(TypeError):
            params.add("not a parameter")  # type: ignore

    def test_contains_not_ok(self):
        params = ParameterMapping((UP_AXIS,))

        self.assertNotIn(123, params)

    def test_user_parameter_ok(self):
        params = ParameterMapping()

        user_param = UserParameter(parameter=TOLERANCE, assigned_value=0.001)
        params.add(user_param)

        self.assertEqual(params["TOLERANCE"].assigned_value, 0.001)
        self.assertEqual(len(params.data["TOLERANCE"]), 1)
        self.assertEqual(params.data["TOLERANCE"][0], user_param)

    def test_user_parameter_overrides_ok(self):
        params = ParameterMapping((TOLERANCE,))

        user_param = UserParameter(parameter=TOLERANCE, assigned_value=0.005)
        params.add(user_param)

        self.assertEqual(params["TOLERANCE"].assigned_value, 0.005)
        self.assertEqual(len(params.data["TOLERANCE"]), 2)
        self.assertEqual(params.data["TOLERANCE"][0], user_param)  # User override
        self.assertEqual(params.data["TOLERANCE"][1], TOLERANCE)  # Original

    def test_user_parameter_multiple_overrides_ok(self):
        params = ParameterMapping((TOLERANCE,))

        user_param1 = UserParameter(parameter=TOLERANCE, assigned_value=0.001)
        user_param2 = UserParameter(parameter=TOLERANCE, assigned_value=0.002)
        params.add(user_param1)
        params.add(user_param2)

        self.assertEqual(params["TOLERANCE"].assigned_value, 0.002)
        self.assertEqual(len(params.data["TOLERANCE"]), 2)
        self.assertEqual(params.data["TOLERANCE"][0], user_param2)  # User override
        self.assertEqual(params.data["TOLERANCE"][1], TOLERANCE)  # Original

    def test_getitem_key_error(self):
        params = ParameterMapping((UP_AXIS,))

        with self.assertRaises(KeyError):
            params["NONEXISTENT"]
