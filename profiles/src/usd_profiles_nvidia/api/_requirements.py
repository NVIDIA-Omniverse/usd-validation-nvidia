# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from dataclasses import dataclass

from ._examples import Example
from ._parameters import Parameter


@dataclass(frozen=True)
class Requirement:
    """
    Args:
        code: A unique identifier of the requirement.
        version: The version of the requirement.
        display_name: A human-readable name of the requirement.
        message: A basic description of the requirement.
        path: Relative path in documentation.
        compatibility: Compatibility of the requirement.
        validator: Validator of the requirement.
        tags: Tags of the requirement.
        parameters: Parameters of the requirement.
        examples: Examples of the requirement.
    """

    code: str
    version: str | None = None
    display_name: str | None = None
    message: str | None = None
    path: str | None = None
    compatibility: str | None = None
    validator: str | None = None
    tags: tuple[str, ...] = ()
    parameters: tuple[Parameter, ...] = ()
    examples: tuple[Example, ...] = ()


@dataclass(frozen=True)
class RequirementRef:
    """
    A reference to a requirement owned by another package.

    Args:
        code: A unique identifier of the referenced requirement.
        version: The version of the referenced requirement.
    """

    code: str
    version: str | None = None
