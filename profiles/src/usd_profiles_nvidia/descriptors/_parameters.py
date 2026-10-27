# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from collections.abc import Sequence

from usd_profiles_nvidia.api import Parameter, ParameterType


def parse_parameter(
    *,
    display_name: str,
    parameter_type: ParameterType | str,
    assigned_value: int | bool | float | str | None = None,
    enum_values: Sequence[str] | None = None,
) -> Parameter:
    """Validate and normalize parsed parameter fields into an API parameter."""
    try:
        parsed_type = ParameterType(parameter_type)
    except (TypeError, ValueError):
        raise ValueError(f"Parameter type must be a ParameterType, got {type(parameter_type)}") from None

    parsed_enum_values = tuple(enum_values) if enum_values is not None else None
    if parsed_type is ParameterType.ENUM and not parsed_enum_values:
        raise ValueError(f"Parameter {display_name} is enum type but has no enum_values")
    if parsed_type is not ParameterType.ENUM and parsed_enum_values:
        raise ValueError(f"Parameter {display_name} is {parsed_type.value} type but has enum_values")

    parsed_value = assigned_value
    if parsed_value is not None:
        match parsed_type:
            case ParameterType.INT:
                try:
                    parsed_value = int(parsed_value)
                except (ValueError, TypeError):
                    raise ValueError(
                        f"Assigned value '{parsed_value}' for int parameter '{display_name}' "
                        "must be a valid integer or numeric string"
                    ) from None
            case ParameterType.BOOL:
                if not isinstance(parsed_value, bool):
                    if isinstance(parsed_value, str) and parsed_value.lower() in {"true", "false"}:
                        parsed_value = parsed_value.lower() == "true"
                    else:
                        raise ValueError(
                            f"Assigned value '{parsed_value}' for bool parameter '{display_name}' "
                            "must be 'true' or 'false' (case-insensitive)"
                        )
            case ParameterType.FLOAT:
                try:
                    parsed_value = float(parsed_value)
                except (ValueError, TypeError):
                    raise ValueError(
                        f"Assigned value '{parsed_value}' for float parameter '{display_name}' "
                        "must be a valid float or numeric string"
                    ) from None
            case ParameterType.ENUM if parsed_value not in (parsed_enum_values or ()):
                raise ValueError(
                    f"Assigned value '{parsed_value}' for enum parameter '{display_name}' "
                    f"is not within declared enum values {parsed_enum_values}"
                )

    return Parameter(
        display_name=display_name,
        type=parsed_type,
        assigned_value=parsed_value,
        enum_values=parsed_enum_values,
    )
