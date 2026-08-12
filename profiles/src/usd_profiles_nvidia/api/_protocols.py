# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from ._examples import Example
from ._parameters import Parameter


@runtime_checkable
class RequirementProtocol(Protocol):
    """
    A protocol definition of requirement.

    Attributes:
        code: A unique identifier of the requirement
        display_name: The name of the requirement (optional)
        message: A basic description of the requirement (optional)
        path: Relative path in documentation (optional)
        validator: Validator of the requirement (optional)
        tags: Tags of the requirement (optional)
        version: The version of the requirement
        parameters: The collection of parameters associated with the requirement (optional)
    """

    code: str
    version: str | None
    display_name: str | None
    message: str | None
    path: str | None
    compatibility: str | None
    validator: str | None
    tags: tuple[str, ...]
    parameters: tuple[Parameter, ...]
    examples: tuple[Example, ...]


@runtime_checkable
class RequirementRefProtocol(Protocol):
    """
    A protocol definition of a requirement reference.

    Attributes:
        code: A unique identifier of the referenced requirement
        version: The version of the referenced requirement
    """

    code: str
    version: str | None


@runtime_checkable
class CapabilityProtocol(Protocol):
    """
    A protocol definition of capability.

    Attributes:
        id: A unique identifier of the capability
        version: The version of the capability
        path: The path to the capability
        requirements: The requirements of the capability
    """

    id: str
    version: str
    path: str
    requirements: list[RequirementProtocol | RequirementRefProtocol]


@runtime_checkable
class FeatureRefProtocol(Protocol):
    """
    A protocol definition of a feature reference.

    Attributes:
        id: A unique identifier of the referenced feature
        version: The version of the referenced feature
    """

    id: str
    version: str | None


@runtime_checkable
class FeatureProtocol(Protocol):
    """
    A protocol definition of feature.

    Attributes:
        id: A unique identifier of the feature
        version: The version of the feature
        path: The path to the feature
        requirements: The requirements of the feature
        dependencies: Other features this feature depends on
        custom_data: Additional authored feature fields
    """

    id: str
    version: str
    path: str
    requirements: list[RequirementProtocol | RequirementRefProtocol]
    dependencies: list[FeatureProtocol | FeatureRefProtocol]
    custom_data: dict[str, Any]


@runtime_checkable
class ProfileFeatureProtocol(Protocol):
    """
    A protocol definition of a profile feature reference.

    Attributes:
        feature: The referenced feature
        optional: Whether the feature is optional in the profile
    """

    feature: FeatureProtocol
    optional: bool


@runtime_checkable
class ProfileProtocol(Protocol):
    """
    A protocol definition of profile.

    Attributes:
        id: A unique identifier of the profile
        version: The version of the profile
        path: The path to the profile
        features: The features of the profile
        capabilities: The capabilities of the profile
        profile_features: The profile feature references
    """

    id: str
    version: str
    path: str
    features: list[FeatureProtocol]
    capabilities: list[CapabilityProtocol]
    profile_features: list[ProfileFeatureProtocol]
