# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from __future__ import annotations

from dataclasses import dataclass

from usd_profiles_nvidia.api import Requirement
from usd_profiles_nvidia.model import (
    BuildCapabilityGraph,
    CapabilityNode,
    Specifications,
)


@dataclass(kw_only=True)
class CapabilityGraphBuilder:
    """Build a capability graph from parsed specifications."""

    graph_namespace: str = ""
    requirement_namespace: str = ""

    def _graph_namespace(self) -> str:
        return self.graph_namespace.rstrip(".")

    def _requirement_namespace(self) -> str:
        return self.requirement_namespace.rstrip(".")

    @staticmethod
    def _qualify_identifier(identifier: str, namespace: str) -> str:
        if not namespace or not identifier:
            return identifier
        if identifier == namespace or identifier.startswith(f"{namespace}."):
            return identifier
        return f"{namespace}.{identifier}"

    def _build_requirement(self, requirement: Requirement, namespace: str) -> Requirement:
        code = self._qualify_identifier(requirement.code, namespace)
        path = requirement.path

        return Requirement(
            code=code,
            display_name=requirement.display_name,
            message=requirement.message,
            version=requirement.version,
            path=f"{path}.html" if path else None,
            compatibility=requirement.compatibility,
            validator=requirement.validator,
            tags=requirement.tags,
            parameters=tuple(requirement.parameters),
            examples=tuple(requirement.examples),
        )

    @staticmethod
    def _validator_id(graph_namespace: str, requirement_code: str) -> str:
        return f"{graph_namespace}:{requirement_code}" if graph_namespace else requirement_code

    def build(self, specifications: Specifications) -> BuildCapabilityGraph:
        graph = BuildCapabilityGraph()
        graph_namespace = self._graph_namespace()
        requirement_namespace = self._requirement_namespace()

        requirement_lookup: dict[str, Requirement] = {}
        for requirement in specifications.requirements:
            requirement_info = self._build_requirement(requirement, requirement_namespace)
            requirement_lookup[requirement_info.code] = requirement_info

        if graph_namespace:
            graph.add_node(
                CapabilityNode(
                    id=graph_namespace,
                    kind="namespace",
                    predecessors=[],
                    docstring=f"{graph_namespace} capabilities",
                ),
                replace=True,
            )

        for capability in specifications.capabilities:
            capability_id = self._qualify_identifier(capability.id, graph_namespace)
            validators: list[str] = []
            capability_requirements: dict[str, Requirement] = {}

            for requirement in capability.requirements:
                requirement_code = self._qualify_identifier(requirement.code, requirement_namespace)
                if requirement.validator:
                    validators.append(self._validator_id(graph_namespace, requirement_code))
                if requirement_code in requirement_lookup:
                    capability_requirements[requirement_code] = requirement_lookup[requirement_code]

            graph.add_node(
                CapabilityNode(
                    id=capability_id,
                    kind="capability",
                    predecessors=[graph_namespace] if graph_namespace else [],
                    validators=validators,
                    domain=capability.id,
                    requirements=capability_requirements,
                ),
                replace=True,
            )

        for feature in specifications.features:
            feature_id = self._qualify_identifier(feature.id, graph_namespace)
            validators = []
            feature_requirements: dict[str, Requirement] = {}
            for requirement_ref in feature.requirements:
                local_code = self._qualify_identifier(requirement_ref.code, requirement_namespace)
                requirement_code = local_code if local_code in requirement_lookup else requirement_ref.code
                validators.append(self._validator_id(graph_namespace, requirement_code))
                if requirement_code in requirement_lookup:
                    feature_requirements[requirement_code] = requirement_lookup[requirement_code]

            predecessors = [graph_namespace] if graph_namespace else []
            for dependency in feature.dependencies:
                predecessor = self._qualify_identifier(dependency.id, graph_namespace)
                if predecessor not in predecessors:
                    predecessors.append(predecessor)

            graph.add_node(
                CapabilityNode(
                    id=feature_id,
                    kind="feature",
                    predecessors=predecessors,
                    validators=validators,
                    requirements=feature_requirements,
                ),
                replace=True,
            )

        for profile in specifications.profiles:
            profile_id = self._qualify_identifier(profile.namespaced_id, graph_namespace)
            predecessors = [
                self._qualify_identifier(profile_feature.feature.id, graph_namespace)
                for profile_feature in profile.features
            ]

            graph.add_node(
                CapabilityNode(
                    id=profile_id,
                    kind="profile",
                    predecessors=predecessors,
                    docstring=profile.message or profile.display_name or "",
                ),
                replace=True,
            )

        return graph
