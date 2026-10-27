# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import unittest

from usd_profiles_nvidia.api import Parameter, ParameterProtocol, ParameterType
from usd_profiles_nvidia.markdown import ParameterParser


class TestParameter(unittest.TestCase):

    def test_parameter_conforms_to_protocol(self):
        parameter = Parameter(display_name="COUNT", type=ParameterType.INT)

        self.assertIsInstance(parameter, ParameterProtocol)

    def test_parameter_int(self):
        """Test int parameter with native int assigned value."""
        param = Parameter(display_name="COUNT", type=ParameterType.INT, assigned_value=10)
        self.assertEqual(param.display_name, "COUNT")
        self.assertEqual(param.type, ParameterType.INT)
        self.assertEqual(param.assigned_value, 10)
        self.assertIsInstance(param.assigned_value, int)
        self.assertIsNone(param.enum_values)

    def test_parameter_bool(self):
        """Test bool parameter with native bool assigned value."""
        param = Parameter(display_name="ENABLED", type=ParameterType.BOOL, assigned_value=True)
        self.assertEqual(param.display_name, "ENABLED")
        self.assertEqual(param.type, ParameterType.BOOL)
        self.assertEqual(param.assigned_value, True)
        self.assertIsInstance(param.assigned_value, bool)
        self.assertIsNone(param.enum_values)

    def test_parameter_enum(self):
        """Test enum parameter with string assigned value."""
        param = Parameter(
            display_name="AXIS",
            type=ParameterType.ENUM,
            assigned_value="X",
            enum_values=("X", "Y", "Z"),
        )
        self.assertEqual(param.display_name, "AXIS")
        self.assertEqual(param.type, ParameterType.ENUM)
        self.assertEqual(param.assigned_value, "X")
        self.assertEqual(param.enum_values, ("X", "Y", "Z"))

    def test_api_parameter_does_not_parse_assigned_value(self):
        param = Parameter(display_name="COUNT", type=ParameterType.INT, assigned_value="10")

        self.assertEqual(param.assigned_value, "10")

    def test_parameter_int_no_default(self):
        param = Parameter(display_name="OPTIONAL_INT", type=ParameterType.INT)
        self.assertEqual(param.display_name, "OPTIONAL_INT")
        self.assertEqual(param.type, ParameterType.INT)
        self.assertIsNone(param.assigned_value)
        self.assertIsNone(param.enum_values)

    def test_parameter_bool_no_default(self):
        param = Parameter(display_name="OPTIONAL_BOOL", type=ParameterType.BOOL)
        self.assertEqual(param.display_name, "OPTIONAL_BOOL")
        self.assertEqual(param.type, ParameterType.BOOL)
        self.assertIsNone(param.assigned_value)
        self.assertIsNone(param.enum_values)

    def test_parameter_negative_int(self):
        """Test negative int parameter."""
        param = Parameter(display_name="NEGATIVE", type=ParameterType.INT, assigned_value=-10)
        self.assertEqual(param.assigned_value, -10)
        self.assertIsInstance(param.assigned_value, int)

    def test_parameter_bool_false(self):
        """Test bool parameter with False."""
        param = Parameter(display_name="DISABLED", type=ParameterType.BOOL, assigned_value=False)
        self.assertEqual(param.assigned_value, False)
        self.assertIsInstance(param.assigned_value, bool)

    def test_parameter_float_from_float(self):
        """Test float parameter with native float assigned value."""
        param = Parameter(display_name="SCALE", type=ParameterType.FLOAT, assigned_value=1.5)
        self.assertEqual(param.assigned_value, 1.5)
        self.assertIsInstance(param.assigned_value, float)


class TestParameterParser(unittest.TestCase):
    """Test the ParameterParser's enum validation logic."""

    def test_parse_enum_with_empty_string_raises_error(self):
        """Test that enum with empty string raises error."""
        with self.assertRaises(ValueError) as context:
            ParameterParser._parse_parameter_type('enum("")')
        self.assertIn("invalid format", str(context.exception).lower())

    def test_parse_enum_with_unquoted_value_raises_error(self):
        """Test that enum with unquoted value raises error."""
        with self.assertRaises(ValueError) as context:
            ParameterParser._parse_parameter_type("enum(X, Y, Z)")
        error_msg = str(context.exception).lower()
        self.assertIn("invalid format", error_msg)
        # Should identify the offending token
        self.assertIn("unrecognised token", error_msg)
        self.assertIn('"x"', error_msg)  # Should identify 'X' as the problem

    def test_parse_enum_with_mixed_quoted_unquoted_raises_error(self):
        """Test that enum with mixed quoted/unquoted values raises error."""
        with self.assertRaises(ValueError) as context:
            ParameterParser._parse_parameter_type('enum("X", Y, "Z")')
        error_msg = str(context.exception).lower()
        self.assertIn("invalid format", error_msg)
        # Should identify Y as the offending unquoted token
        self.assertIn("unrecognised token", error_msg)
        self.assertIn('"y"', error_msg)

    def test_parse_enum_with_empty_string_in_list_raises_error(self):
        """Test that enum with empty string among valid values raises error."""
        with self.assertRaises(ValueError) as context:
            ParameterParser._parse_parameter_type('enum("A", "", "C")')
        self.assertIn("invalid format", str(context.exception).lower())

    def test_parse_enum_valid_single_value(self):
        """Test that enum with single valid quoted value works."""
        param_type, enum_values = ParameterParser._parse_parameter_type('enum("A")')
        self.assertEqual(param_type, ParameterType.ENUM)
        self.assertEqual(enum_values, ("A",))

    def test_parse_enum_valid_multiple_values(self):
        """Test that enum with multiple valid quoted values works."""
        param_type, enum_values = ParameterParser._parse_parameter_type('enum("X", "Y", "Z")')
        self.assertEqual(param_type, ParameterType.ENUM)
        self.assertEqual(enum_values, ("X", "Y", "Z"))

    def test_parse_enum_with_spaces(self):
        """Test that enum with spaces around values works."""
        param_type, enum_values = ParameterParser._parse_parameter_type('enum( "A" , "B" , "C" )')
        self.assertEqual(param_type, ParameterType.ENUM)
        self.assertEqual(enum_values, ("A", "B", "C"))

    def test_parse_enum_case_insensitive_keyword(self):
        """Test that enum keyword is case-insensitive."""
        param_type, enum_values = ParameterParser._parse_parameter_type('ENUM("A", "B")')
        self.assertEqual(param_type, ParameterType.ENUM)
        self.assertEqual(enum_values, ("A", "B"))

    def test_parse_enum_with_double_comma_raises_error(self):
        """Test that enum with double comma raises error."""
        with self.assertRaises(ValueError) as context:
            ParameterParser._parse_parameter_type('enum("A",, "B")')
        self.assertIn("invalid format", str(context.exception).lower())

    def test_parse_enum_with_trailing_comma_raises_error(self):
        """Test that enum with trailing comma raises error."""
        with self.assertRaises(ValueError) as context:
            ParameterParser._parse_parameter_type('enum("A", "B",)')
        self.assertIn("invalid format", str(context.exception).lower())

    def test_parse_enum_with_leading_comma_raises_error(self):
        """Test that enum with leading comma raises error."""
        with self.assertRaises(ValueError) as context:
            ParameterParser._parse_parameter_type('enum(,"A", "B")')
        self.assertIn("invalid format", str(context.exception).lower())

    def test_parse_float_type_case_insensitive(self):
        """Test that float type keyword is case-insensitive."""
        for s in ("float", "FLOAT", "Float"):
            param_type, enum_values = ParameterParser._parse_parameter_type(s)
            self.assertEqual(param_type, ParameterType.FLOAT)
            self.assertIsNone(enum_values)
