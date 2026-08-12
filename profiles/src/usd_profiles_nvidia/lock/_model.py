# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from dataclasses import dataclass, field

LOCK_VERSION = 1


class ProfilesLockError(ValueError):
    """Raised when a profiles lock cannot be read, written, or validated."""


@dataclass(frozen=True)
class SourceLockEntry:
    """The source location and fingerprint for a locked feature version."""

    path: str
    hash: str


@dataclass(frozen=True)
class FeatureLockEntry:
    """A locked source fingerprint for one feature id/version."""

    key: str
    source: SourceLockEntry


@dataclass
class ProfilesLock:
    """The parsed contents of a profiles.lock file."""

    version: int = LOCK_VERSION
    features: dict[str, FeatureLockEntry] = field(default_factory=dict)


@dataclass(frozen=True)
class LockProblem:
    kind: str
    key: str
    message: str


@dataclass(frozen=True)
class LockCheckResult:
    """Summary returned by lock checks."""

    path: str
    checked: int = 0
    skipped: bool = False
