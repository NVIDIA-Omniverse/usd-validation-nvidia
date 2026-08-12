# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from dataclasses import dataclass

from ._model import LockProblem, ProfilesLock, ProfilesLockError


@dataclass(frozen=True)
class ProfilesLockValidator:
    """Compare profiles lock contents and format actionable error messages."""

    def compare(self, expected: ProfilesLock, current: ProfilesLock) -> tuple[LockProblem, ...]:
        problems: list[LockProblem] = []
        for key, current_entry in current.features.items():
            expected_entry = expected.features.get(key)
            if expected_entry is None:
                problems.append(
                    LockProblem(
                        kind="missing",
                        key=key,
                        message=f"Missing profiles.lock entry for feature {key}.",
                    )
                )
            elif expected_entry.source.hash != current_entry.source.hash:
                problems.append(
                    LockProblem(
                        kind="changed",
                        key=key,
                        message=(
                            f"Feature {key} changed its locked source fingerprint without changing its version "
                            f"(expected {expected_entry.source.hash}, got {current_entry.source.hash})."
                        ),
                    )
                )

        for key in expected.features:
            if key not in current.features:
                problems.append(
                    LockProblem(
                        kind="stale",
                        key=key,
                        message=f"Stale profiles.lock entry for feature {key}.",
                    )
                )

        return tuple(problems)

    def raise_for_problems(self, path: str, problems: tuple[LockProblem, ...]) -> None:
        if not problems:
            return
        details = "\n".join(f"- {problem.message}" for problem in problems)
        raise ProfilesLockError(
            f"Profiles lock check failed for {path}:\n"
            f"{details}\n"
            "Bump the affected feature version, or update the lock after adding/removing feature versions."
        )
