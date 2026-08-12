# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from ._model import FeatureLockEntry, LOCK_VERSION, ProfilesLock, ProfilesLockError, SourceLockEntry

DEFAULT_LOCK_FILE = "profiles.lock"


@dataclass(frozen=True)
class ProfilesLockFile:
    """Read and write a profiles.lock file."""

    path: str

    @classmethod
    def resolve(cls, docs_root: str) -> ProfilesLockFile:
        return cls(os.path.join(docs_root, DEFAULT_LOCK_FILE))

    @staticmethod
    def _load_toml(path: str) -> dict:
        try:
            import tomllib
        except ModuleNotFoundError:
            import tomli as tomllib

        with open(path, "rb") as f:
            return tomllib.load(f)

    @staticmethod
    def _toml_string(value: str) -> str:
        return json.dumps(value, ensure_ascii=True)

    def exists(self) -> bool:
        return os.path.exists(self.path)

    def read(self) -> ProfilesLock:
        if not self.exists():
            raise FileNotFoundError(f"Profiles lock file not found: {self.path}")

        data = self._load_toml(self.path)
        version = data.get("version")
        if version != LOCK_VERSION:
            raise ProfilesLockError(f"Unsupported profiles lock version: {version!r}")

        features_data = data.get("features", {})
        if not isinstance(features_data, dict):
            raise ProfilesLockError("profiles.lock field 'features' must be a table.")

        features: dict[str, FeatureLockEntry] = {}
        for key, entry in features_data.items():
            if not isinstance(entry, dict):
                raise ProfilesLockError(f"Lock entry for {key!r} must be a table.")
            source = entry.get("source")
            if not isinstance(source, dict):
                raise ProfilesLockError(f"Lock entry for {key!r} must have a 'source' table.")
            source_path = source.get("path")
            source_hash = source.get("hash")
            if not isinstance(source_path, str):
                raise ProfilesLockError(f"Lock entry for {key!r} source must have a string 'path'.")
            if not isinstance(source_hash, str):
                raise ProfilesLockError(f"Lock entry for {key!r} source must have a string 'hash'.")
            features[key] = FeatureLockEntry(
                key=key,
                source=SourceLockEntry(path=source_path, hash=source_hash),
            )

        return ProfilesLock(version=version, features=features)

    def write(self, lock: ProfilesLock) -> None:
        directory = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(directory, exist_ok=True)

        lines = [
            f"version = {lock.version}",
            "",
        ]
        for key in sorted(lock.features):
            entry = lock.features[key]
            lines.extend(
                [
                    f"[features.{self._toml_string(key)}.source]",
                    f"path = {self._toml_string(entry.source.path)}",
                    f"hash = {self._toml_string(entry.source.hash)}",
                    "",
                ]
            )

        with open(self.path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines))
