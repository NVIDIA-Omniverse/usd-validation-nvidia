# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import json
import logging
import os
from bisect import insort
from collections import defaultdict
from collections.abc import Iterator
from functools import singledispatchmethod
from typing import Any, Generic, TypeVar

from usd_profiles_nvidia.json import JsonDeserialize
from usd_profiles_nvidia.model import HasMetadata, IdVersion

logger = logging.getLogger(__name__)

K = TypeVar("K")
V = TypeVar("V")


class Registry(Generic[K, V]):
    """
    A generic registry of key-value pairs.
    """

    def __init__(self):
        self._registry: dict[K, V] = {}

    def add(self, key: K, value: V) -> None:
        self._registry[key] = value

    def __getitem__(self, key: K) -> V:
        return self._registry[key]

    def __iter__(self) -> Iterator[V]:
        return iter(self._registry.values())

    def __len__(self) -> int:
        return len(self._registry)

    def get(self, key: K, default: V | None = None) -> V | None:
        return self._registry.get(key, default)

    def keys(self) -> Iterator[K]:
        return iter(self._registry.keys())

    def values(self) -> Iterator[V]:
        return iter(self._registry.values())

    def items(self) -> Iterator[tuple[K, V]]:
        return iter(self._registry.items())


class VersionedRegistry(Registry[IdVersion, V]):
    """
    A registry of values with versioned keys.
    """

    def __init__(self):
        super().__init__()
        self._registry_by_id: dict[str, list[IdVersion]] = defaultdict(list)

    def create_key(self, value: V) -> IdVersion | None:
        raise NotImplementedError("Subclasses must implement this method")

    def add(self, value: V) -> None:
        key: IdVersion | None = self.create_key(value)
        if key is None:
            return
        super().add(key, value)
        insort(self._registry_by_id[key.id], key)

    def find(self, key: IdVersion) -> V | None:
        keys: list[IdVersion] = self._registry_by_id[key.id]
        if not keys:
            return None
        elif key.version is None:
            return self[keys[-1]]
        else:
            return self.get(key, None)

    def latest_keys(self) -> list[IdVersion]:
        return [values[-1] for values in self._registry_by_id.values() if values]

    def latest_values(self) -> list[V]:
        return [self[key] for key in self.latest_keys()]


class PersistentVersionedRegistry(VersionedRegistry[V]):
    """
    A versioned registry of values that are stored in JSON files.
    """

    @singledispatchmethod
    def __init__(self, arg) -> None:
        raise TypeError(f"Cannot create {type(self).__name__} from {type(arg)}")

    @__init__.register
    def _(self, directory: str) -> None:
        super().__init__()
        for value in self._iter_values(directory):
            self.add(value)

    @__init__.register
    def _(self, values: list) -> None:
        super().__init__()
        for value in values:
            self.add(value)

    def _iter_values(self, directory: str) -> Iterator[V]:
        for filename in os.listdir(directory):
            if not filename.endswith(".json"):
                continue
            filepath: str = os.path.join(directory, filename)
            with open(filepath, encoding="utf-8") as f:
                try:
                    result: Any = json.load(f, cls=JsonDeserialize)
                    if isinstance(result, HasMetadata):
                        if not result.metadata.path:
                            result.metadata.path = filepath

                    yield from self.create_values(result)
                except Exception as e:
                    logger.error(f"Error loading JSON file {filename}: {e}")

    def create_values(self, result: Any) -> list[V]:
        return [result]

    def find_all(self, keys: list[IdVersion]) -> list[V]:
        result = []
        for key in keys:
            value: V | None = self.find(key)
            if value is not None:
                result.append(value)
        return result
