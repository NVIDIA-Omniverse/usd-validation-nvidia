# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

import dataclasses
from collections import UserDict
from collections.abc import Iterable, Iterator
from enum import Enum
from typing import Protocol, runtime_checkable

__all__ = [
    "Parameter",
    "ParameterMapping",
    "ParameterType",
]


class ParameterType(str, Enum):
    """Valid parameter types for requirements."""

    INT = "int"
    BOOL = "bool"
    FLOAT = "float"
    ENUM = "enum"


@runtime_checkable
class Parameter(Protocol):
    """
    Protocol for parameter definition objects.

    Args:
        display_name: The display name of the parameter
        type: The type of the parameter (int, bool, float, or enum)
        assigned_value: The assigned value of the parameter
        enum_values: The possible enum values (only for enum type)
    """

    display_name: str
    type: ParameterType
    assigned_value: int | bool | float | str | None
    enum_values: tuple[str, ...] | None


@dataclasses.dataclass(frozen=True)
class UserParameter(Parameter):
    """User-level parameter override.

    Wraps an immutable Parameter (like an Enum member or frozen dataclass)
    and only stores the overridden assigned_value. All other properties are delegated
    to the wrapped parameter. This satisfies the Parameter Protocol.

    This represents a user-level override (e.g., from CLI --parameter arguments) which
    takes precedence over requirement-level and feature-level parameter values.
    """

    parameter: Parameter
    assigned_value: int | bool | float | str | None

    def __post_init__(self):
        """Validate that assigned_value type matches the parameter's type."""
        if self.assigned_value is None:
            return

        param_type = self.parameter.type
        value = self.assigned_value

        if param_type == ParameterType.INT and not isinstance(value, int):
            raise TypeError(f"Parameter '{self.parameter.display_name}' expects int, got {type(value).__name__}")
        elif param_type == ParameterType.FLOAT and not isinstance(value, int | float):
            raise TypeError(f"Parameter '{self.parameter.display_name}' expects float, got {type(value).__name__}")
        elif param_type == ParameterType.BOOL and not isinstance(value, bool):
            raise TypeError(f"Parameter '{self.parameter.display_name}' expects bool, got {type(value).__name__}")
        elif param_type == ParameterType.ENUM:
            if not isinstance(value, str):
                raise TypeError(f"Parameter '{self.parameter.display_name}' expects str, got {type(value).__name__}")
            # Validate enum value is in the allowed set
            if self.parameter.enum_values and value not in self.parameter.enum_values:
                raise ValueError(
                    f"Value '{value}' is not valid for enum parameter '{self.parameter.display_name}'. "
                    f"Valid values: {self.parameter.enum_values}"
                )

    @property
    def display_name(self) -> str:
        return self.parameter.display_name

    @property
    def type(self) -> ParameterType:
        return self.parameter.type

    @property
    def enum_values(self) -> tuple[str, ...] | None:
        return self.parameter.enum_values


class ParameterMapping(UserDict):
    """Dict-like collection of Parameters, auto-keyed by display_name.

    Stores an ordered list of Parameters for each parameter name to support
    multi-level overrides (requirement level, feature level, user level).
    When accessing a parameter, returns the first one (most specific override).
    Iterates over resolved values, not keys.
    """

    def __init__(self, parameters: Iterable[Parameter] | None = None):
        """Initialize from an iterable of Parameters.

        Each parameter name maps to a list of Parameter objects, ordered by
        specificity (most specific first).
        """
        super().__init__()
        if parameters:
            for param in parameters:
                self.add(param)

    def add(self, parameter: Parameter) -> None:
        """Add a parameter to the top of the stack for its display_name.

        Parameters are always prepended to the front of the list (top of stack).
        The most recently added parameter takes precedence when accessing.

        Args:
            parameter: The parameter to add

        Raises:
            TypeError: If parameter doesn't conform to Parameter protocol
        """
        if not isinstance(parameter, Parameter):
            raise TypeError(f"Expected Parameter protocol instance, got {type(parameter).__name__}")
        parameters: list[Parameter] = self.data.setdefault(parameter.display_name, [])
        if isinstance(parameter, UserParameter):
            parameters[:] = [p for p in parameters if not isinstance(p, UserParameter)]
        parameters.insert(0, parameter)

    def __getitem__(self, key: str) -> Parameter:
        return self.data[key][0]

    def __iter__(self) -> Iterator[Parameter]:
        return iter(self.values())

    def __contains__(self, name: str | Parameter) -> bool:
        key: str = name.display_name if isinstance(name, Parameter) else name
        return key in self.data

    def keys(self) -> list[str]:
        return list(self.data.keys())

    def values(self) -> list[Parameter]:
        return [value[0] for value in self.data.values()]

    def items(self) -> list[tuple[str, Parameter]]:
        return [(name, value[0]) for name, value in self.data.items()]
