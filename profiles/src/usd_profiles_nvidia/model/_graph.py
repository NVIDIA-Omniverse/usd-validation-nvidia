# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from dataclasses import replace as dataclass_replace

from usd_profiles_nvidia.api import Requirement

logger = logging.getLogger(__name__)

SCHEMA_VERSION = "usd-profiles/capability-dag"

# Valid values for the ``kind`` field on a capability node.
VALID_KINDS = frozenset({"namespace", "capability", "feature", "profile"})


@dataclass(slots=True)
class CapabilityNode:
    """A single node in the capability DAG."""

    id: str
    kind: str = "capability"
    predecessors: list[str] = field(default_factory=list)
    validators: list[str] = field(default_factory=list)
    docstring: str = ""
    domain: str = ""
    requirements: dict[str, Requirement] = field(default_factory=dict)


@dataclass(slots=True)
class BuildCapabilityGraph:
    """Build-time capability graph generated from parsed specifications."""

    _nodes: dict[str, CapabilityNode] = field(default_factory=dict, init=False)

    @property
    def nodes(self) -> Mapping[str, CapabilityNode]:
        return self._nodes

    def add_node(self, node: CapabilityNode, *, replace: bool = False) -> bool:
        """
        Add a node to the build graph.

        Args:
            node: Node to add.
            replace: If True, replace any existing node with the same id.

        Returns:
            True if the node was added or replaced, False if it was skipped.
        """
        if node.kind not in VALID_KINDS:
            logger.warning(
                "Capability '%s' has unknown kind '%s'; treating as 'capability'",
                node.id,
                node.kind,
            )
            node = dataclass_replace(node, kind="capability")

        if node.id in self._nodes and not replace:
            logger.warning(
                "Duplicate capability '%s'; keeping first definition",
                node.id,
            )
            return False

        self._nodes[node.id] = node
        return True

    def merge(self, other: BuildCapabilityGraph) -> None:
        """Merge another build graph into this one."""
        for node_id, node in other.nodes.items():
            if node_id in self._nodes:
                logger.warning(
                    "Merge conflict: capability '%s' already exists; keeping existing definition",
                    node_id,
                )
                continue
            self.add_node(node)

    def __len__(self) -> int:
        return len(self._nodes)

    def __contains__(self, id: str) -> bool:
        return id in self._nodes
