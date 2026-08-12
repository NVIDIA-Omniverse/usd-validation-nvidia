# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from collections.abc import Iterator
from dataclasses import InitVar, dataclass, field

from usd_profiles_nvidia.api import Requirement
from usd_profiles_nvidia.model import Parameter


@dataclass
class ParameterStore:
    """
    A store of unique parameters extracted from requirements.

    This store validates parameter consistency: parameters with the same name
    must have identical type, assigned value, and enum values.

    Args:
        requirements: An iterable of requirements to extract parameters from.

    Raises:
        ValueError: If parameters with the same name have conflicting definitions.
    """

    requirements: InitVar[list[Requirement]]
    _parameters: dict[str, Parameter] = field(default_factory=dict)

    def __post_init__(self, requirements: list[Requirement]) -> None:
        for requirement in requirements:
            for param in requirement.parameters:
                if param.display_name in self._parameters:
                    if self._parameters[param.display_name] == param:
                        continue
                    raise ValueError(f"Parameter {param.display_name} already exists.")
                self._parameters[param.display_name] = param

    def __iter__(self) -> Iterator[Parameter]:
        return iter(sorted(self._parameters.values(), key=lambda p: p.display_name))

    def __len__(self) -> int:
        return len(self._parameters)

    def __contains__(self, name: str) -> bool:
        return name in self._parameters

    def get(self, name: str) -> Parameter | None:
        return self._parameters.get(name)
