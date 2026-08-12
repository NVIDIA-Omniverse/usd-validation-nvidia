# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Capability DAG runtime graph loading and query helpers."""

from __future__ import annotations

import copy
import json
import logging
from dataclasses import dataclass, field
from dataclasses import fields as dataclass_fields
from pathlib import Path
from typing import Any

from usd_profiles_nvidia.api import Requirement
from usd_profiles_nvidia.model import (
    CapabilityNode,
    Example,
    ExampleResult,
    ExampleSnippet,
    ExampleSnippetLanguage,
    Metadata,
    Parameter,
    ParameterType,
)
from usd_profiles_nvidia.model._graph import SCHEMA_VERSION

__all__ = [
    "CapabilityGraph",
    "CapabilityGraphDeserializer",
    "encode_graph",
]

logger = logging.getLogger(__name__)

_CAPABILITY_NODE_FIELDS = {field.name for field in dataclass_fields(CapabilityNode) if field.name != "id"}
_EXAMPLE_FIELDS = {field.name for field in dataclass_fields(Example)}
_EXAMPLE_SNIPPET_FIELDS = {field.name for field in dataclass_fields(ExampleSnippet)}
_PARAMETER_FIELDS = {field.name for field in dataclass_fields(Parameter)}
_REQUIREMENT_FIELDS = {field.name for field in dataclass_fields(Requirement) if field.name != "code"}


class CapabilityGraphDeserializer(json.JSONDecoder):
    """JSON decoder and normalizer for ``capabilities.json`` graph data."""

    def __init__(self, *args, **kwargs):
        kwargs.pop("object_hook", None)
        super().__init__(*args, object_hook=self.object_hook, **kwargs)

    @classmethod
    def object_hook(cls, dct: dict[str, Any]) -> Any:
        if dct.get("schema") == SCHEMA_VERSION and isinstance(dct.get("capabilities"), dict):
            return cls.decode_graph(dct)
        return dct

    @classmethod
    def decode_graph(cls, data: dict[str, Any]) -> CapabilityGraph:
        return CapabilityGraph(
            schema=data.get("schema", SCHEMA_VERSION),
            nodes={
                cap_id: cls.decode_node(cap_id, cap_data) for cap_id, cap_data in data.get("capabilities", {}).items()
            },
        )

    @classmethod
    def decode_node(cls, cap_id: str, cap_data: dict[str, Any]) -> CapabilityNode:
        values = {key: value for key, value in cap_data.items() if key in _CAPABILITY_NODE_FIELDS}
        return CapabilityNode(
            **{
                **values,
                "id": cap_id,
                "kind": values.get("kind", "capability"),
                "predecessors": list(values.get("predecessors") or ()),
                "validators": list(values.get("validators") or ()),
                "requirements": {
                    code: cls.decode_requirement(code, requirement, cap_id=cap_id)
                    for code, requirement in (values.get("requirements") or {}).items()
                },
            }
        )

    @classmethod
    def decode_requirement(cls, code: str, data: dict[str, Any], *, cap_id: str = "") -> Requirement:
        values = {key: value for key, value in data.items() if key in _REQUIREMENT_FIELDS}
        metadata = data.get("metadata")
        if "display_name" not in values and "name" in data:
            values["display_name"] = data["name"]
        if "path" not in values and isinstance(metadata, dict):
            values["path"] = Metadata(metadata.get("path")).path if metadata.get("path") else None
        context = f"capability node {cap_id!r} requirement {code!r}" if cap_id else f"requirement {code!r}"
        return Requirement(
            **{
                **values,
                "code": code,
                "tags": tuple(values.get("tags") or ()),
                "parameters": tuple(cls.decode_parameter(parameter) for parameter in values.get("parameters") or ()),
                "examples": tuple(
                    cls.decode_example(example, context=context) for example in values.get("examples") or ()
                ),
            }
        )

    @classmethod
    def decode_parameter(cls, data: dict[str, Any]) -> Parameter:
        values = {key: value for key, value in data.items() if key in _PARAMETER_FIELDS}
        return Parameter(
            **{
                **values,
                "type": ParameterType(values["type"]),
            }
        )

    @classmethod
    def decode_example(cls, data: dict[str, Any], *, context: str = "") -> Example:
        values = {key: value for key, value in data.items() if key in _EXAMPLE_FIELDS}
        example_context = f"{context} example" if context else "example"
        return Example(
            **{
                **values,
                "snippet": cls.decode_example_snippet(
                    cls._required(values, "snippet", example_context),
                    context=example_context,
                ),
                "display_name": values.get("display_name") or data.get("name") or "",
                "result": ExampleResult(cls._required(values, "result", example_context)),
            }
        )

    @classmethod
    def decode_example_snippet(cls, data: dict[str, Any], *, context: str = "") -> ExampleSnippet:
        values = {key: value for key, value in data.items() if key in _EXAMPLE_SNIPPET_FIELDS}
        snippet_context = f"{context} snippet" if context else "example snippet"
        return ExampleSnippet(
            **{
                **values,
                "language": ExampleSnippetLanguage(cls._required(values, "language", snippet_context)),
            }
        )

    @staticmethod
    def _required(data: dict[str, Any], field: str, context: str) -> Any:
        if field not in data:
            raise ValueError(f"Missing required field {field!r} in {context}")
        return data[field]


@dataclass(slots=True)
class CapabilityGraph:
    """
    Capability DAG DTO with query methods.

    Load from ``capabilities.json`` data or files, then query predecessors,
    validators, requirements, and profiles.
    """

    schema: str = SCHEMA_VERSION
    nodes: dict[str, CapabilityNode] = field(default_factory=dict)

    # Loading

    @classmethod
    def load_from_dict(cls, data: dict[str, Any]) -> CapabilityGraph:
        """
        Create a graph from a parsed JSON dict.

        Args:
            data: Dict matching the ``capabilities.json`` schema.
        """
        return CapabilityGraphDeserializer.decode_graph(data)

    @classmethod
    def load_from_json(cls, path: str | Path) -> CapabilityGraph:
        """
        Create a graph from a ``capabilities.json`` file.

        Args:
            path: Path to the JSON file.
        """
        with open(path, encoding="utf-8") as f:
            return json.load(f, cls=CapabilityGraphDeserializer)

    def merge(self, other: CapabilityGraph) -> None:
        """
        Merge another graph into this one. Duplicate node ids are skipped
        with a warning.

        Args:
            other: Graph to merge from.
        """
        for cap_id, node in other.nodes.items():
            if cap_id in self.nodes:
                logger.warning(
                    "Merge conflict: capability '%s' already exists; keeping existing definition",
                    cap_id,
                )
                continue
            self.nodes[cap_id] = copy.deepcopy(node)

    # Queries

    def is_capability(self, id: str) -> bool:
        """Return True if *id* is a registered capability."""
        return id in self.nodes

    def is_profile(self, id: str) -> bool:
        """Return True if *id* is a registered profile."""
        node = self.nodes.get(id)
        return node is not None and node.kind == "profile"

    def get_kind(self, id: str) -> str:
        """Return the ``kind`` tag for *id*, or empty string if unknown."""
        node = self.nodes.get(id)
        return node.kind if node else ""

    def get_docstring(self, id: str) -> str:
        """Return the docstring for *id*, or empty string if unknown."""
        node = self.nodes.get(id)
        return node.docstring if node else ""

    def get_domain(self, id: str) -> str:
        """Return the domain for *id*, or empty string if unknown."""
        node = self.nodes.get(id)
        return node.domain if node else ""

    def get_predecessors(self, id: str) -> list[str]:
        """Return the direct predecessors of *id*."""
        node = self.nodes.get(id)
        return list(node.predecessors) if node else []

    def get_transitive_predecessors(self, id: str) -> list[str]:
        """
        Return all transitive predecessors of *id* (BFS), not including
        *id* itself.
        """
        if id not in self.nodes:
            return []

        visited: dict[str, None] = {}
        queue: list[str] = list(self.get_predecessors(id))

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited[current] = None
            for pred in self.get_predecessors(current):
                if pred not in visited:
                    queue.append(pred)

        return list(visited)

    def get_validators(self, id: str) -> list[str]:
        """Return validators declared directly on *id*."""
        node = self.nodes.get(id)
        return list(node.validators) if node else []

    def get_all_validators_for_capability(self, id: str) -> list[str]:
        """
        Return all validators for *id* and its transitive predecessors.
        Duplicates are removed (first occurrence wins).
        """
        if id not in self.nodes:
            return []

        validators: dict[str, None] = {}

        for node_id in [id, *self.get_transitive_predecessors(id)]:
            validators.update(dict.fromkeys(self.get_validators(node_id)))

        return list(validators)

    def get_all_capabilities(self) -> list[str]:
        """Return all registered capability ids, sorted."""
        return sorted(self.nodes.keys())

    def get_all_profiles(self) -> list[str]:
        """Return all registered profile ids, sorted."""
        return sorted(cap_id for cap_id, node in self.nodes.items() if node.kind == "profile")

    # Requirement queries

    def get_requirement(self, code: str) -> Requirement | None:
        """
        Find a requirement by code across all nodes.

        Args:
            code: Requirement code (e.g. ``"HI.004"``).

        Returns:
            The requirement if found, else ``None``.
        """
        for node in self.nodes.values():
            if code in node.requirements:
                return node.requirements[code]
        return None

    def get_requirements(self, id: str) -> list[Requirement]:
        """
        Return all requirements declared directly on node *id*.

        Args:
            id: Capability/feature/profile node id.

        Returns:
            List of requirements (empty for nodes without requirements).
        """
        node = self.nodes.get(id)
        if not node:
            return []
        return list(node.requirements.values())

    def get_all_requirements(self) -> list[Requirement]:
        """
        Return all requirements across all nodes, deduplicated by code.

        Returns:
            List of requirements, sorted by code.
        """
        seen: dict[str, Requirement] = {}
        for node in self.nodes.values():
            for code, requirement in node.requirements.items():
                if code not in seen:
                    seen[code] = requirement
        return sorted(seen.values(), key=lambda requirement: requirement.code)

    # Filtering

    def filter_by_namespace(self, prefix: str, *, include_predecessors: bool = False) -> list[str]:
        """
        Return capability ids matching the given namespace prefix.

        Args:
            prefix: Dot-separated prefix (e.g. ``"com.nvidia.simready"``).
            include_predecessors: If True, also include transitive
                predecessors of matching capabilities.

        Returns:
            Sorted list of matching capability ids.
        """
        matched: set[str] = set()
        for cap_id in self.nodes:
            if cap_id == prefix or cap_id.startswith(prefix + "."):
                matched.add(cap_id)

        if not matched:
            return []

        if include_predecessors:
            expanded = set(matched)
            for cap_id in matched:
                for pred in self.get_transitive_predecessors(cap_id):
                    expanded.add(pred)
            return sorted(expanded)

        return sorted(matched)

    # Serialization

    def to_json(self, path: str | Path, *, indent: int = 2) -> None:
        """Write the graph to a ``capabilities.json`` file."""
        _write_json(self, path, indent=indent)

    def __len__(self) -> int:
        return len(self.nodes)

    def __contains__(self, id: str) -> bool:
        return id in self.nodes


def encode_graph(graph: CapabilityGraph) -> dict[str, Any]:
    """Return the JSON object for a capability graph."""
    from usd_profiles_nvidia.json import JsonSerialize

    return json.loads(json.dumps(graph, cls=JsonSerialize))


def _write_json(graph: CapabilityGraph, path: str | Path, *, indent: int) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(encode_graph(graph), f, indent=indent)
        f.write("\n")
