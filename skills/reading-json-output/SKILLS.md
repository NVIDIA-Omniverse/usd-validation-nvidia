---
name: reading-json-output
description: Reading NVIDIA USD Validation JSON reports. Use when interpreting --json-output, mapping profile failures to features and requirements, grouping rule issues, understanding severity, or deciding what an agent should fix next.
---

# Reading JSON Output

## Overview

`nvidia_usd_validate --json-output report.json` writes the most useful artifact for agents and CI. The JSON report has a top-level pass/fail status, optional profile/feature metadata, and rule-level issues.

Use this skill after running validation. For CLI commands, see `skills/validate-asset/SKILLS.md`.

## Minimal Shape

The top-level object is shaped like this:

```json
{
    "status": "FAIL",
    "profiles": [],
    "features": [],
    "rules": [
        {
            "rule": {"type": "RULE", "name": "SomeRuleChecker"},
            "status": "FAIL",
            "issues": []
        }
    ]
}
```

Important fields:

| Field | Meaning |
|-------|---------|
| `status` | `PASS` when no selected issues remain, otherwise `FAIL` |
| `profiles[]` | Present when validation is profile-scoped |
| `features[]` | Present when validation is feature- or capability-scoped outside a profile |
| `rules[]` | Per-rule pass/fail status and nested `issues[]` |
| `rules[].issues[]` | Actual validation issues; there is no top-level `issues[]` list |

> **Source:** `src/usd_validation_nvidia/_json_reports.py` defines the JSON encoder.
>
> **Source:** `tests/test_json_reports.py` covers top-level `status`, `profiles`, `features`, `rules`, `requirement`, and `suggestions`.

## Profile Tree

When `--profile Prop-Robotics-Neutral` is active, expect `profiles[]` entries like:

```json
{
    "id": "Prop-Robotics-Neutral",
    "version": "1.0.0",
    "status": "FAIL",
    "features": [
        {
            "id": "FET004_BASE_NEUTRAL",
            "version": "0.1.0",
            "status": "FAIL",
            "requirements": [
                {
                    "code": "RB.MB.001",
                    "version": "1.0.0",
                    "status": "FAIL"
                }
            ]
        }
    ]
}
```

Read it top-down:

1. Find failing `profiles[]`.
2. Within each failing profile, find failing `features[]`.
3. Within each failing feature, collect failing `requirements[]`.
4. Map those requirement codes to `rules[].issues[]` entries with matching `issue.requirement.code`.

The `features[]` field under a profile may represent capability-like generated groups. Use the IDs and requirement codes as the durable signals.

## Rule Issues

Each failing rule contains one or more issues:

```json
{
    "type": "ISSUE",
    "message": "failure text",
    "severity": "FAILURE",
    "rule": {"type": "RULE", "name": "SomeRuleChecker"},
    "at": {"type": "PRIM", "path": "/Root/Geom"},
    "requirement": {"code": "VG.010", "version": "1.0.0"},
    "suggestion": {"type": "SUGGESTION", "message": "first fix"},
    "suggestions": [
        {"type": "SUGGESTION", "message": "first fix"}
    ]
}
```

Key issue fields:

| Field | Meaning |
|-------|---------|
| `severity` | `ERROR`, `FAILURE`, `WARNING`, or `INFO` |
| `message` | Human-readable failure detail |
| `rule.name` | Checker class that produced the issue |
| `requirement.code` | Compliance requirement, present when the rule is requirement-backed |
| `at` | Location such as prim, property, layer, stage, schema, or spec |
| `suggestions[]` | Available automatic fixes, if the rule provides them |
| `suggestion` | First suggestion for backward compatibility |

## Triage Order

1. Handle `ERROR` first. These usually mean tooling/runtime problems: unreadable assets, unresolved USD plugins, bad resolver context, or validator exceptions.
2. Group `FAILURE` by `requirement.code` and `at.path`. These block profile compliance.
3. Review `WARNING` with the project policy. Warnings may be quality guidance rather than delivery blockers.
4. Use `suggestions[]` to decide whether `--fix` can help.
5. Re-run the same profile and compare the new JSON report.

## Quick Python Reader

Use this when an agent needs to summarize failures from a JSON artifact:

```python
import json
from pathlib import Path

report = json.loads(Path("reports/sample_prop.validation.json").read_text())
for rule in report.get("rules", []):
    for issue in rule.get("issues", []):
        req = issue.get("requirement", {})
        at = issue.get("at", {})
        print(
            issue.get("severity"),
            req.get("code", "<no requirement>"),
            rule.get("rule", {}).get("name"),
            at.get("path", "<no path>"),
            issue.get("message"),
        )
```

## Common Pitfalls

- Looking for `report["issues"]`; issues are nested under `report["rules"][i]["issues"]`.
- Treating a rule failure without `requirement` as a profile requirement failure. It may still matter, but it cannot be mapped directly to the profile tree.
- Ignoring `ERROR` because it is not a `FAILURE`. Errors often invalidate the run.
- Using `suggestion` only and missing additional entries in `suggestions[]`.
- Comparing two reports without using the same validation scope and package versions.
