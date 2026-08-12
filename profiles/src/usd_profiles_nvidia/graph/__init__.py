# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Runtime capability DAG library.

Provides :class:`CapabilityGraph` for loading, merging, and querying capability
DAG definitions from ``capabilities.json`` files.

This is the Python equivalent of the C++ ``UsdProfilesCapabilityRegistry`` but
works standalone without USD or UsdValidation dependencies.
"""

from ._builder import CapabilityGraphBuilder
from ._graph import CapabilityGraph, CapabilityGraphDeserializer, encode_graph

__all__ = [
    "CapabilityGraph",
    "CapabilityGraphBuilder",
    "CapabilityGraphDeserializer",
    "encode_graph",
]
