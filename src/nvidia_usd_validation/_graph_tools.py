# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from dataclasses import dataclass, field

__all__ = [
    "DisjointSet",
]


@dataclass(slots=True)
class DisjointSet:
    _parent: dict[int, int] = field(default_factory=dict, init=False)
    _rank: dict[int, int] = field(default_factory=dict, init=False)
    _count: int = 0

    def make_set(self, x: int) -> None:
        if x not in self._parent:
            self._parent[x] = x
            self._rank[x] = 0
            self._count += 1

    def find(self, x: int) -> int:
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def union(self, x: int, y: int) -> None:
        x = self.find(x)
        y = self.find(y)
        if x == y:
            return
        if self._rank[x] < self._rank[y]:
            x, y = y, x
        self._parent[y] = x
        if self._rank[x] == self._rank[y]:
            self._rank[x] += 1
        self._count -= 1

    @property
    def connected(self) -> bool:
        return self._count == 1
