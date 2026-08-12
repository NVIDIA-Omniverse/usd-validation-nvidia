# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from usd_profiles_nvidia.api import Feature

from ._builder import ProfilesLockBuilder
from ._file import ProfilesLockFile
from ._model import LockCheckResult, LockProblem, ProfilesLock
from ._validator import ProfilesLockValidator


@dataclass(frozen=True)
class ProfilesLockManager:
    """Check and update an optional profiles.lock file."""

    lock_file: ProfilesLockFile
    builder: ProfilesLockBuilder = field(default_factory=ProfilesLockBuilder)
    validator: ProfilesLockValidator = field(default_factory=ProfilesLockValidator)

    @classmethod
    def resolve(cls, docs_root: str) -> ProfilesLockManager:
        return cls(ProfilesLockFile.resolve(docs_root))

    def check(self, features: Iterable[Feature]) -> LockCheckResult:
        if not self.lock_file.exists():
            return LockCheckResult(path=self.lock_file.path, skipped=True)

        expected = self.lock_file.read()
        current = self.builder.build(features)
        problems = self.validator.compare(expected, current)
        self.validator.raise_for_problems(self.lock_file.path, problems)
        return LockCheckResult(path=self.lock_file.path, checked=len(current.features))

    def _check_update(self, existing: ProfilesLock, current: ProfilesLock) -> None:
        changed_existing = tuple(
            LockProblem(
                kind="changed",
                key=key,
                message=(
                    f"Refusing to update existing feature {key}; its source hash changed "
                    f"from {existing.features[key].source.hash} to {entry.source.hash}."
                ),
            )
            for key, entry in current.features.items()
            if key in existing.features and existing.features[key].source.hash != entry.source.hash
        )
        self.validator.raise_for_problems(self.lock_file.path, changed_existing)

    def update(self, features: Iterable[Feature]) -> ProfilesLock:
        """
        Write the current profiles lock.

        Checks existing feature id/version entries before writing: changing the
        source hash for an existing key raises instead of silently blessing the
        change.
        """
        current = self.builder.build(features)
        if self.lock_file.exists():
            existing = self.lock_file.read()
            self._check_update(existing, current)

        self.lock_file.write(current)
        return current
