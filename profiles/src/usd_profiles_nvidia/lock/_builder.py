# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable

from usd_profiles_nvidia.api import Feature, Requirement, RequirementRef

from ._model import FeatureLockEntry, ProfilesLock, ProfilesLockError, SourceLockEntry

LOCK_ALGORITHM = "sha256"


class ProfilesLockBuilder:
    """Build canonical feature source fingerprints from API Feature objects."""

    def requirement_key(self, requirement: Requirement | RequirementRef) -> str:
        version = requirement.version
        return f"{requirement.code}@{version}" if version else requirement.code

    def feature_key(self, feature: Feature) -> str:
        return f"{feature.id}@{feature.version}" if feature.version else feature.id

    def feature_hash_inputs(self, feature: Feature) -> list[str]:
        # The path is stored for traceability; requirement refs define the versioned source fingerprint.
        return list(map(self.requirement_key, sorted(feature.requirements, key=self.requirement_key)))

    def source_hash(self, values: list[str]) -> str:
        payload = json.dumps(values, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        return f"{LOCK_ALGORITHM}:{hashlib.sha256(payload).hexdigest()}"

    def build(self, features: Iterable[Feature]) -> ProfilesLock:
        entries: dict[str, FeatureLockEntry] = {}
        for feature in sorted(features, key=self.feature_key):
            key = self.feature_key(feature)
            if key in entries:
                raise ProfilesLockError(f"Duplicate feature version found while building profiles lock: {key}")
            hash_inputs = self.feature_hash_inputs(feature)
            entries[key] = FeatureLockEntry(
                key=key,
                source=SourceLockEntry(
                    path=feature.path,
                    hash=self.source_hash(hash_inputs),
                ),
            )
        return ProfilesLock(features=entries)
