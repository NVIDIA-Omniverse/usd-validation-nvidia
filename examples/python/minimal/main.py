# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Minimal Python example for NVIDIA USD Validation.

Run from the repository root:
    python examples/python/minimal/main.py

Set USD_VALIDATION_PROFILE to validate against a registered profile:
    USD_VALIDATION_PROFILE=Prop-Robotics-Neutral python examples/python/minimal/main.py
"""

from __future__ import annotations

import os
from pathlib import Path

from usd_validation_nvidia import ProfileRegistry, ValidationEngine


ASSET = Path(__file__).parent / "assets" / "sample_prop.usda"


def _find_profile(profile_id: str):
    for profile in ProfileRegistry().latest_values():
        if profile.id == profile_id:
            return profile
    return None


def main() -> int:
    profile_id = os.environ.get("USD_VALIDATION_PROFILE")

    # snippet: create-engine
    engine = ValidationEngine(init_rules=profile_id is None)
    # snippet-end: create-engine

    # snippet: enable-profile
    if profile_id:
        profile = _find_profile(profile_id)
        if profile is None:
            available = ", ".join(p.id for p in ProfileRegistry().latest_values()) or "<none>"
            raise SystemExit(f"Profile {profile_id!r} is not registered. Available profiles: {available}")
        engine.enable_profile(profile)
    # snippet-end: enable-profile

    # snippet: validate-asset
    result = engine.validate(str(ASSET))
    # snippet-end: validate-asset

    # snippet: print-issues
    issues = result.issues()
    if not issues:
        print(f"PASS: {ASSET}")
        return 0

    for issue in issues:
        rule = issue.rule.__name__ if issue.rule else "<no rule>"
        requirement = f" [{issue.requirement.code}]" if issue.requirement else ""
        print(f"{issue.severity.name}{requirement} {rule}: {issue.message}")
    return 1
    # snippet-end: print-issues


if __name__ == "__main__":
    raise SystemExit(main())
