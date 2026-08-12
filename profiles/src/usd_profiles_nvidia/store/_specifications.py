# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from functools import singledispatchmethod

from usd_profiles_nvidia.model import Specifications

from ._capabilities import CapabilityStore
from ._examples import ExampleStore
from ._features import FeatureStore
from ._parameters import ParameterStore
from ._profiles import ProfileStore
from ._requirements import RequirementStore


class SpecificationsStore:
    """
    Collects all stores into a single object.

    Args:
        directory: The directory to load the catalog from.
        specifications: A Specifications object to use directly.
    """

    @singledispatchmethod
    def __init__(self, arg) -> None:
        raise TypeError(f"Cannot create SpecificationsStore from {type(arg)}")

    @__init__.register
    def _(self, directory: str) -> None:
        self.requirements = RequirementStore(directory)
        self.capabilities = CapabilityStore(directory)
        self.profiles = ProfileStore(directory)
        self.features = FeatureStore(directory)
        self.parameters = ParameterStore(self.requirements)
        self.examples = ExampleStore(self.requirements)

    @__init__.register
    def _(self, specifications: Specifications) -> None:
        self.requirements = RequirementStore(specifications.requirements)
        self.capabilities = CapabilityStore(specifications.capabilities)
        self.profiles = ProfileStore(specifications.profiles)
        self.features = FeatureStore(specifications.features)
        self.parameters = ParameterStore(self.requirements)
        self.examples = ExampleStore(self.requirements)
