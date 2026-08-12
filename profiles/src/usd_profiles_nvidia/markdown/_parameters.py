# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Parameter parsing for requirements."""

import re
from dataclasses import dataclass

from usd_profiles_nvidia.model import Parameter, ParameterType

from ._parser import Section

# Regex to extract individual quoted strings from enum values (must not be empty)
_ENUM_VALUE_RE = re.compile(r'"([^"]+)"')
# Regex to validate that content contains only quoted strings, commas, and whitespace
_ENUM_CONTENT_VALIDATION_RE = re.compile(r'^(\s*"[^"]+"\s*)(,\s*"[^"]+"\s*)*$')


@dataclass
class ParameterParser:
    """
    Parser for requirement parameters.

    Args:
        parameters_section: The parameters section from the document.
    """

    parameters_section: Section

    @staticmethod
    def _parse_parameter_type(type_str: str) -> tuple[ParameterType, list[str] | None]:
        """
        Parse a parameter type string.

        Args:
            type_str: The type string to parse (e.g., "int", "bool", "enum("X", "Y", "Z")").

        Returns:
            A tuple of (ParameterType, enum_values). enum_values is None for non-enum types.

        Raises:
            ValueError: If the type string is invalid.
        """
        type_str = type_str.strip()

        enum_remainder = type_str[4:].lstrip() if type_str[:4].lower() == "enum" else ""
        if enum_remainder.startswith("(") and enum_remainder.endswith(")"):
            # Extract quoted string values from the enum using regex
            values_str = enum_remainder[1:-1].strip()

            # Validate that the content only contains properly quoted strings and commas
            # This catches unquoted values, empty strings, and other malformed inputs
            if not _ENUM_CONTENT_VALIDATION_RE.fullmatch(values_str):
                # Try to identify the offending token for better error messages
                # Look for unquoted tokens (non-whitespace, non-comma, non-quote sequences)
                unquoted_match = re.search(r'(?:^|,)\s*([^",\s][^",]*)', values_str)
                offending_token = unquoted_match.group(1) if unquoted_match else None

                error_msg = (
                    f"Enum values must be non-empty quoted strings separated by commas. "
                    f"Found invalid format: enum({values_str}). "
                )
                if offending_token:
                    error_msg += f'Unrecognised token: "{offending_token}". '
                error_msg += 'Expected format: enum("A", "B", "C")'
                raise ValueError(error_msg)

            # Extract the individual enum values
            enum_values = _ENUM_VALUE_RE.findall(values_str)

            # Verify completeness: ensure we extracted values
            if not enum_values:
                raise ValueError(
                    f"Enum type must specify at least one non-empty quoted string value, "
                    f'e.g. enum("A", "B"): {type_str}'
                )

            # Verify no empty strings slipped through
            if any(not val for val in enum_values):
                raise ValueError(f"Enum values cannot be empty strings. " f"Found empty value in: {type_str}")

            return (ParameterType.ENUM, enum_values)

        # Check for simple types
        lower_type = type_str.lower()
        if lower_type == "int":
            return (ParameterType.INT, None)
        elif lower_type == "bool":
            return (ParameterType.BOOL, None)
        elif lower_type == "float":
            return (ParameterType.FLOAT, None)
        else:
            raise ValueError(f"Unknown parameter type: {type_str}")

    def parse(self) -> list[Parameter]:
        """
        Parse parameters from the parameters section.

        Returns:
            A list of Parameter objects.
        """
        parameters: list[Parameter] = []

        if not self.parameters_section or not self.parameters_section.tables:
            return parameters

        # Fail if multiple tables are present (likely an authoring error)
        if len(self.parameters_section.tables) > 1:
            raise ValueError(
                f"Multiple parameter tables found in Parameters section. "
                f"Expected 1 table, found {len(self.parameters_section.tables)}. "
                f"Please consolidate into a single parameters table."
            )

        # Expect a table with columns: Parameter, Type, Default Value
        param_table = self.parameters_section.tables[0]

        # Track parameter names to detect duplicates
        seen_names: set[str] = set()

        # Skip header row (first row)
        for row in param_table[1:]:
            if len(row) < 3:
                continue

            param_name = row[0].content.strip()
            param_type_str = row[1].content.strip()
            param_default = row[2].content.strip() if row[2].content.strip() else None

            if not param_name or not param_type_str:
                continue

            # Detect duplicate parameter names
            if param_name in seen_names:
                raise ValueError(f"Duplicate parameter name '{param_name}' found in parameters table")
            seen_names.add(param_name)

            # Parse the type and enum values
            param_type, enum_values = self._parse_parameter_type(param_type_str)

            # Parameter.__post_init__ will validate enum assigned values
            parameters.append(
                Parameter(
                    display_name=param_name,
                    type=param_type,
                    assigned_value=param_default,
                    enum_values=enum_values,
                )
            )

        return parameters
