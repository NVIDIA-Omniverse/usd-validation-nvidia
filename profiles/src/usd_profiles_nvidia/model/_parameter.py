# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from dataclasses import dataclass

from usd_profiles_nvidia.api import ParameterType

from ._naming import Naming


@dataclass(slots=True)
class Parameter:
    """
    Represents a parameter for a requirement.

    Args:
        display_name: The display name of the parameter
        type: The type of the parameter (int, bool, float, or enum)
        assigned_value: The assigned value of the parameter
        enum_values: The possible enum values (only for enum type)
    """

    display_name: str
    type: ParameterType
    assigned_value: int | bool | float | str | None = None
    enum_values: list[str] | None = None

    @property
    def enum_name(self) -> str:
        return Naming.enum_name(self.display_name)

    def _validate_type(self) -> None:
        """Validate the parameter type."""
        if not isinstance(self.type, ParameterType):
            raise ValueError(f"Parameter type must be a ParameterType, got {type(self.type)}")

    def _validate_type_consistency(self) -> None:
        """Validate that enum_values is consistent with the parameter type."""
        if self.type == ParameterType.ENUM and not self.enum_values:
            raise ValueError(f"Parameter {self.display_name} is enum type but has no enum_values")
        if self.type != ParameterType.ENUM and self.enum_values:
            raise ValueError(f"Parameter {self.display_name} is {self.type.value} type but has enum_values")

    def _validate_and_normalize_assigned(self) -> None:
        """Validate and normalize the assigned value based on parameter type."""
        if self.assigned_value is None:
            return

        if self.type == ParameterType.INT:
            self._validate_int_assigned()
        elif self.type == ParameterType.BOOL:
            self._validate_and_normalize_bool_assigned()
        elif self.type == ParameterType.FLOAT:
            self._validate_float_assigned()
        elif self.type == ParameterType.ENUM:
            self._validate_enum_assigned()

    def _validate_int_assigned(self) -> None:
        """Validate and convert the assigned value to an integer."""
        if isinstance(self.assigned_value, int):
            return  # Already correct type

        # Convert string to int
        try:
            converted = int(self.assigned_value)
            self.assigned_value = converted
        except (ValueError, TypeError):
            raise ValueError(
                f"Assigned value '{self.assigned_value}' for int parameter '{self.display_name}' "
                "must be a valid integer or numeric string"
            )

    def _validate_and_normalize_bool_assigned(self) -> None:
        """Validate and convert the boolean assigned value to a Python bool."""
        if isinstance(self.assigned_value, bool):
            return  # Already correct type

        # Convert string to bool
        if isinstance(self.assigned_value, str):
            normalized = self.assigned_value.lower()
            if normalized == "true":
                self.assigned_value = True
            elif normalized == "false":
                self.assigned_value = False
            else:
                raise ValueError(
                    f"Assigned value '{self.assigned_value}' for bool parameter '{self.display_name}' "
                    "must be 'true' or 'false' (case-insensitive)"
                )
        else:
            raise ValueError(
                f"Assigned value '{self.assigned_value}' for bool parameter '{self.display_name}' "
                "must be a boolean or string 'true'/'false'"
            )

    def _validate_float_assigned(self) -> None:
        """Validate and convert the assigned value to a float."""
        try:
            converted = float(self.assigned_value)
            self.assigned_value = converted
        except (ValueError, TypeError):
            raise ValueError(
                f"Assigned value '{self.assigned_value}' for float parameter '{self.display_name}' "
                "must be a valid float or numeric string"
            )

    def _validate_enum_assigned(self) -> None:
        """Validate that the enum assigned value is one of the declared values."""
        if self.enum_values and self.assigned_value not in self.enum_values:
            raise ValueError(
                f"Assigned value '{self.assigned_value}' for enum parameter '{self.display_name}' "
                f"is not within declared enum values {self.enum_values}"
            )

    def __post_init__(self):
        """Validate and normalize parameter constraints."""
        self._validate_type()
        self._validate_type_consistency()
        self._validate_and_normalize_assigned()
