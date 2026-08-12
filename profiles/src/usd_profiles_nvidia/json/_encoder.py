# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import json
import re
from dataclasses import dataclass
from functools import singledispatchmethod
from typing import Any

from usd_profiles_nvidia.api import Capability, Feature, FeatureRef, Requirement, RequirementRef
from usd_profiles_nvidia.graph._graph import CapabilityGraph
from usd_profiles_nvidia.model import (
    BuildCapabilityGraph,
    CapabilityNode,
    Compatibility,
    Example,
    ExampleSnippet,
    IdVersion,
    Metadata,
    Parameter,
    Profile,
    ProfileFeature,
    Tag,
    Version,
)
from usd_profiles_nvidia.model._graph import SCHEMA_VERSION

__all__ = ["JsonSerialize"]


@dataclass
class _InlineDirective:
    value: str


_INLINE_DIRECTIVE_RE = re.compile(r"\{[^}`]+\}`([^`]*)`")


class JsonSerialize(json.JSONEncoder):
    @singledispatchmethod
    def default(self, o):
        return super().default(o)

    @default.register
    def _(self, o: BuildCapabilityGraph):
        return {
            "schema": SCHEMA_VERSION,
            "capabilities": {node_id: node for node_id, node in sorted(o.nodes.items())},
        }

    @default.register
    def _(self, o: CapabilityGraph):
        return {
            "schema": o.schema,
            "capabilities": {node_id: node for node_id, node in sorted(o.nodes.items())},
        }

    @default.register
    def _(self, o: CapabilityNode):
        entry: dict[str, Any] = {"kind": o.kind}
        if o.predecessors:
            entry["predecessors"] = o.predecessors
        if o.validators:
            entry["validators"] = o.validators
        if o.docstring:
            entry["docstring"] = o.docstring
        if o.domain:
            entry["domain"] = o.domain
        if o.requirements:
            entry["requirements"] = o.requirements
        return entry

    @default.register
    def _(self, o: Requirement):
        return {
            "code": o.code,
            "version": o.version,
            "name": o.display_name,
            "compatibility": o.compatibility,
            "tags": o.tags if o.tags else None,
            "validator": _InlineDirective(o.validator) if o.validator else None,
            "parameters": o.parameters,
            "metadata": Metadata(path=o.path) if o.path else None,
            "message": o.message,
            "examples": o.examples,
        }

    @default.register
    def _(self, o: Parameter):
        return {
            "display_name": o.display_name,
            "type": o.type.value,
            "assigned_value": o.assigned_value,
            "enum_values": o.enum_values,
        }

    @default.register
    def _(self, o: ExampleSnippet):
        return {
            "language": o.language.value,
            "content": o.content,
        }

    @default.register
    def _(self, o: Example):
        return {
            "snippet": o.snippet,
            "name": o.display_name,
            "result": o.result.value,
        }

    @default.register
    def _(self, o: Capability):
        return {
            "capability": {
                "id": o.id,
                "version": o.version,
                "requirements": o.requirements,
                "metadata": Metadata(path=o.path) if o.path else None,
            }
        }

    @default.register
    def _(self, o: Profile):
        return {
            "profile": {
                "id": o.id,
                "version": o.version,
                "name": o.display_name,
                "description": o.message,
                "requirements": [],
                "capabilities": [],
                "features": o.features,
                "metadata": o.metadata,
            }
        }

    @default.register
    def _(self, o: Feature):
        feature = {
            **o.custom_data,
            "id": o.id,
            "version": o.version,
            "requirements": o.requirements,
            "dependencies": o.dependencies,
            "metadata": Metadata(path=o.path) if o.path else None,
        }
        return {
            "feature": feature,
        }

    @default.register
    def _(self, o: Metadata):
        return {
            "path": o.html_path,
            "internal_path": o.md_path,
        }

    @default.register
    def _(self, o: _InlineDirective):
        if value := _INLINE_DIRECTIVE_RE.search(o.value):
            return value.group(1)
        return o.value

    @default.register
    def _(self, o: Version):
        return str(o)

    @default.register
    def _(self, o: ProfileFeature):
        return {
            "feature": o.feature,
            "optional": o.optional,
        }

    @default.register
    def _(self, o: IdVersion):
        if o.version is None:
            return o.id
        else:
            return f"{o.id}@{o.version}"

    @default.register
    def _(self, o: RequirementRef):
        if o.version is None:
            return o.code
        else:
            return f"{o.code}@{o.version}"

    @default.register
    def _(self, o: FeatureRef):
        if o.version is None:
            return o.id
        else:
            return f"{o.id}@{o.version}"

    @default.register
    def _(self, o: Compatibility):
        return o.display_name

    @default.register
    def _(self, o: Tag):
        return o.display_name
