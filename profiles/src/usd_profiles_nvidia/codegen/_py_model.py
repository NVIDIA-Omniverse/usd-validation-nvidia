# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from usd_profiles_nvidia.api import (
    Capability,
    Example,
    Feature,
    FeatureRef,
    Parameter,
    Requirement,
    RequirementRef,
)
from usd_profiles_nvidia.model import IdVersion, Naming, Profile, Version
from usd_profiles_nvidia.model import ProfileFeature as ModelProfileFeature
from usd_profiles_nvidia.store import (
    CapabilityStore,
    ExampleStore,
    FeatureStore,
    ParameterStore,
    ProfileStore,
    RequirementStore,
    SpecificationsStore,
)


def _namespaced_id(identifier: str, namespace: str) -> str:
    if not namespace or not identifier:
        return identifier
    prefix = f"{namespace.rstrip('.')}."
    return identifier if identifier.startswith(prefix) else f"{prefix}{identifier}"


def _strip_namespace(identifier: str, namespace: str) -> str:
    prefix = f"{namespace.rstrip('.')}."
    return identifier.removeprefix(prefix) if namespace and identifier.startswith(prefix) else identifier


@dataclass(frozen=True)
class PyRequirement:
    requirement: Requirement
    namespace: str = ""

    @property
    def version(self) -> str | None:
        return str(self.requirement.version) if self.requirement.version is not None else None

    @property
    def display_name(self) -> str:
        return self.requirement.display_name or self.requirement.code

    @property
    def message(self) -> str | None:
        return self.requirement.message

    @property
    def path(self) -> str:
        return self.requirement.path or ""

    @property
    def html_path(self) -> str | None:
        path = self.requirement.path
        return f"{path}.html" if path else None

    @property
    def compatibility(self) -> str | None:
        return self.requirement.compatibility

    @property
    def validator(self) -> str | None:
        return self.requirement.validator

    @property
    def tags(self) -> tuple[str, ...]:
        return self.requirement.tags

    @property
    def parameters(self) -> tuple[Parameter, ...]:
        return tuple(self.requirement.parameters)

    @property
    def examples(self) -> tuple[Example, ...]:
        return tuple(self.requirement.examples)

    @property
    def namespaced_id(self) -> str:
        return _namespaced_id(self.requirement.code, self.namespace)

    @property
    def enum_id(self) -> str:
        return Naming.enum_name(self.requirement.code, namespace=self.namespace)

    @property
    def enum_id_version(self) -> str:
        return Naming.enum_name(self.requirement.code, self.version, namespace=self.namespace)


@dataclass(frozen=True)
class PyCapability:
    capability: Capability
    namespace: str = ""

    @property
    def version(self) -> str | None:
        return str(self.capability.version) if self.capability.version is not None else None

    @property
    def namespaced_id(self) -> str:
        return _namespaced_id(self.capability.id, self.namespace)

    @property
    def enum_id(self) -> str:
        return Naming.enum_name(self.capability.id, namespace=self.namespace)

    @property
    def enum_id_version(self) -> str:
        return Naming.enum_name(self.capability.id, self.version, namespace=self.namespace)

    @property
    def class_name(self) -> str:
        return Naming.class_name(self.capability.id, namespace=self.namespace)

    @property
    def html_path(self) -> str | None:
        path = self.capability.path
        return f"{path}.html" if path else None

    @property
    def requirements(self) -> list[PyRequirement]:
        return [PyRequirement(requirement, self.namespace) for requirement in self.capability.requirements]


@dataclass(frozen=True)
class PyFeature:
    feature: Feature
    namespace: str = ""

    @property
    def version(self) -> str | None:
        return str(self.feature.version) if self.feature.version is not None else None

    @property
    def namespaced_id(self) -> str:
        return _namespaced_id(self.feature.id, self.namespace)

    @property
    def enum_id(self) -> str:
        return Naming.enum_name(self.feature.id, namespace=self.namespace)

    @property
    def enum_id_version(self) -> str:
        return Naming.enum_name(self.feature.id, self.version, namespace=self.namespace)

    @property
    def html_path(self) -> str | None:
        path = self.feature.path
        return f"{path}.html" if path else None

    @property
    def requirements(self) -> list[Requirement | RequirementRef]:
        return self.feature.requirements

    @property
    def dependencies(self) -> list[Feature | FeatureRef]:
        return self.feature.dependencies


@dataclass(frozen=True)
class PyProfile:
    profile: Profile
    namespace: str = ""

    @property
    def version(self) -> str | None:
        return str(self.profile.version) if self.profile.version is not None else None

    @property
    def namespaced_id(self) -> str:
        return _namespaced_id(self.profile.id, self.namespace)

    @property
    def enum_id(self) -> str:
        return Naming.enum_name(self.profile.id, namespace=self.namespace)

    @property
    def enum_id_version(self) -> str:
        return Naming.enum_name(self.profile.id, self.version, namespace=self.namespace)

    @property
    def html_path(self) -> str | None:
        path = self.profile.metadata.path
        return f"{path}.html" if path else None

    @property
    def features(self) -> list[ModelProfileFeature]:
        return self.profile.features


@dataclass(frozen=True)
class PyRequirementStore:
    store: RequirementStore
    namespace: str = ""

    def _wrap(self, requirement: Requirement) -> PyRequirement:
        return PyRequirement(requirement, self.namespace)

    def __iter__(self) -> Iterator[PyRequirement]:
        return (self._wrap(requirement) for requirement in self.store)

    def __len__(self) -> int:
        return len(self.store)

    def find(self, key: Any) -> PyRequirement | None:
        if requirement := self.store.find(key):
            return self._wrap(requirement)
        elif isinstance(key, IdVersion):
            local_key = IdVersion(_strip_namespace(key.id, self.namespace), key.version)
            if local_key != key and (requirement := self.store.find(local_key)):
                return self._wrap(requirement)
        else:
            return None

    def find_all(self, keys: list[RequirementRef]) -> list[PyRequirement | RequirementRef]:
        requirements: list[PyRequirement | RequirementRef] = []
        for key in keys:
            lookup_key = IdVersion(key.code, Version(key.version) if key.version else None)
            if requirement := self.find(lookup_key):
                requirements.append(requirement)
            else:
                requirements.append(RequirementRef(key.code, str(key.version) if key.version is not None else None))
        return requirements

    @staticmethod
    def is_requirement_ref(requirement: PyRequirement | RequirementRef) -> bool:
        return isinstance(requirement, RequirementRef)

    def latest_values(self) -> list[PyRequirement]:
        return [self._wrap(requirement) for requirement in self.store.latest_values()]


@dataclass(frozen=True)
class PyCapabilityStore:
    store: CapabilityStore
    namespace: str = ""

    def _wrap(self, capability: Capability) -> PyCapability:
        return PyCapability(capability, self.namespace)

    def __iter__(self) -> Iterator[PyCapability]:
        return (self._wrap(capability) for capability in self.store)

    def __len__(self) -> int:
        return len(self.store)

    def find(self, key: Any) -> PyCapability | None:
        if capability := self.store.find(key):
            return self._wrap(capability)
        return None

    def latest_values(self) -> list[PyCapability]:
        return [self._wrap(capability) for capability in self.store.latest_values()]


@dataclass(frozen=True)
class PyFeatureStore:
    store: FeatureStore
    namespace: str = ""

    def _wrap(self, feature: Feature) -> PyFeature:
        return PyFeature(feature, self.namespace)

    @staticmethod
    def _unwrap(feature: Feature | PyFeature) -> Feature:
        return feature.feature if isinstance(feature, PyFeature) else feature

    def __iter__(self) -> Iterator[PyFeature]:
        return (self._wrap(feature) for feature in self.store)

    def __len__(self) -> int:
        return len(self.store)

    def find(self, key: FeatureRef | IdVersion) -> PyFeature | None:
        if feature := self.store.find(key):
            return self._wrap(feature)
        elif isinstance(key, FeatureRef):
            version = Version(key.version) if key.version else None
            return self.find(IdVersion(key.id, version))
        elif isinstance(key, IdVersion):
            local_key = IdVersion(_strip_namespace(key.id, self.namespace), key.version)
            if local_key != key and (feature := self.store.find(local_key)):
                return self._wrap(feature)
        return None

    def latest_values(self) -> list[PyFeature]:
        return [self._wrap(feature) for feature in self.store.latest_values()]

    def resolve_requirements(self, feature: Feature | PyFeature) -> list[RequirementRef]:
        return self.store.resolve_requirements(self._unwrap(feature))

    def find_dependencies(self, feature: Feature | PyFeature) -> list[PyFeature | FeatureRef]:
        dependencies: list[PyFeature | FeatureRef] = []
        for dependency in self._unwrap(feature).dependencies:
            if resolved := self.find(dependency):
                dependencies.append(resolved)
            else:
                dependencies.append(dependency)
        return dependencies

    @staticmethod
    def is_feature_ref(feature: PyFeature | FeatureRef) -> bool:
        return isinstance(feature, FeatureRef)


@dataclass(frozen=True)
class PyProfileStore:
    store: ProfileStore
    namespace: str = ""

    def _wrap(self, profile: Profile) -> PyProfile:
        return PyProfile(profile, self.namespace)

    def __iter__(self) -> Iterator[PyProfile]:
        return (self._wrap(profile) for profile in self.store)

    def __len__(self) -> int:
        return len(self.store)

    def find(self, key: Any) -> PyProfile | None:
        if profile := self.store.find(key):
            return self._wrap(profile)
        return None

    def latest_values(self) -> list[PyProfile]:
        return [self._wrap(profile) for profile in self.store.latest_values()]


@dataclass(frozen=True)
class PythonStoreView:
    store: SpecificationsStore
    namespace: str = ""

    @property
    def requirements(self) -> PyRequirementStore:
        return PyRequirementStore(self.store.requirements, self.namespace)

    @property
    def capabilities(self) -> PyCapabilityStore:
        return PyCapabilityStore(self.store.capabilities, self.namespace)

    @property
    def profiles(self) -> PyProfileStore:
        return PyProfileStore(self.store.profiles, self.namespace)

    @property
    def features(self) -> PyFeatureStore:
        return PyFeatureStore(self.store.features, self.namespace)

    @property
    def parameters(self) -> ParameterStore:
        return self.store.parameters

    @property
    def examples(self) -> ExampleStore:
        return self.store.examples
