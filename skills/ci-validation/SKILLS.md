---
name: ci-validation
description: Integrating NVIDIA USD Validation into CI pipelines. Use when adding profile validation to GitLab, GitHub Actions, or other automation, preserving JSON/CSV artifacts, choosing exit-code behavior, or making validation deterministic.
---

# CI Validation

## Overview

CI should run a deterministic validation scope, write structured artifacts, and let the CLI exit code fail the job when selected issues are found. Do not rely on profile auto-detection for delivery gates.

## Minimal CI Shape

```bash
python -m pip install "usd-validation-nvidia[usd,numpy]"
nvidia_usd_validate --json-output validation.json path/to/asset.usd
```

Upload `validation.json` even when the job fails.

For a delivery profile gate, also install the project-specific generated profile package or custom plugin that registers the profile. If CI generates profile code or docs, install `usd-profiles-nvidia` for those steps. Confirm the profile appears in `nvidia_usd_validate --help`, then pass it explicitly:

```bash
nvidia_usd_validate --profile Prop-Robotics-Neutral --json-output validation.json path/to/asset.usd
```

## GitLab Example

```yaml
validate-usd:
  image: python:3.11
  stage: test
  script:
    - python -m pip install --upgrade pip
    - python -m pip install "usd-validation-nvidia[usd,numpy]"
    - nvidia_usd_validate --json-output validation.json path/to/asset.usd
  artifacts:
    when: always
    paths:
      - validation.json
```

## GitHub Actions Example

```yaml
name: Validate USD

on:
  pull_request:
  push:

jobs:
  validate-usd:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: python -m pip install --upgrade pip
      - run: python -m pip install "usd-validation-nvidia[usd,numpy]"
      - run: nvidia_usd_validate --json-output validation.json path/to/asset.usd
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: usd-validation
          path: validation.json
```

Configure the package index or credentials according to the target CI environment if a project-specific generated profile package, custom plugin, or `usd-profiles-nvidia` codegen dependency is not available from the default index.

## Multiple Assets

For a fixed list of assets, run the same validation scope for each asset and keep one report per asset:

```bash
nvidia_usd_validate --json-output reports/asset_a.json assets/asset_a.usd
nvidia_usd_validate --json-output reports/asset_b.json assets/asset_b.usd
```

For repository-wide discovery, use the project build system or a short wrapper script to enumerate files, but keep each CLI invocation scoped consistently. If this is a delivery gate, use the required profile for every asset.

## Policy Choices

| Choice | Recommendation |
|--------|----------------|
| Validation scope | Use default validation for smoke tests; pass the exact delivery profile for delivery gates |
| Artifacts | Always upload JSON; optionally upload CSV for humans |
| Fixing | Do not use `--fix` in validation-only CI |
| Warnings | Decide policy explicitly; do not assume all warnings are blockers |
| Package versions | Pin or lock versions for reproducible gates |
| Resolver context | Match the authoring/deployment environment so references resolve the same way |

## Reading Results in CI

If CI needs a short summary, parse `rules[].issues[]` from the JSON:

```python
import json
from pathlib import Path

report = json.loads(Path("validation.json").read_text())
failures = []
for rule in report.get("rules", []):
    for issue in rule.get("issues", []):
        if issue.get("severity") in {"ERROR", "FAILURE"}:
            failures.append((rule["rule"]["name"], issue.get("message")))

print(f"{len(failures)} blocking validation issue(s)")
for rule_name, message in failures:
    print(f"- {rule_name}: {message}")
```

## Common Pitfalls

- Letting CI validate whatever profiles are auto-detected instead of the required delivery profile.
- Failing the job without preserving the JSON report.
- Installing `usd-validation-nvidia` but not the generated profile package or plugin needed for the selected profile.
- Running validation from a different working directory than asset references expect.
- Changing package versions between local and CI without noticing different registered profiles or rules.
