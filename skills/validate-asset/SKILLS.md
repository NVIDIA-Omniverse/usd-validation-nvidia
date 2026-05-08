---
name: validate-asset
description: Validating OpenUSD assets with NVIDIA USD Validation from the CLI. Use when running nvidia_usd_validate on USD/USDZ assets, discovering installed validation scopes, selecting profiles/features/capabilities/requirements/categories/rules, validating against Prop-Robotics-Neutral, or troubleshooting validation-scope errors.
---

# Validate Asset

## Overview

Use this skill when the validation environment already exists and the task is to validate an asset. For Python project scaffolding and package installation, use `skills/project-setup-python/SKILLS.md`.

The CLI entry point is:

```bash
nvidia_usd_validate
```

The module entry point is useful when the console script is not on `PATH`:

```bash
python -m usd_validation_nvidia
```

## Discover Available Validation Scope

Always discover scope from the target environment:

```bash
nvidia_usd_validate --help
```

The help text is generated from currently registered entry points. It lists valid choices for:

| Scope | CLI flags | Typical use |
|-------|-----------|-------------|
| Profile | `--profile`, `--enable-profile`, `--disable-profile` | Delivery target checks such as `Prop-Robotics-Neutral` |
| Feature | `--feature`, `--enable-feature`, `--disable-feature` | User-facing capability slices |
| Capability | `--capability` | Generated capability groups |
| Requirement | `--requirement` | Single compliance requirement code/version |
| Category | `--category`, `--enable-category`, `--disable-category` | Rule family such as geometry or material |
| Rule | `--rule`, `--enable-rule`, `--disable-rule` | One checker class |

Treat names as case-sensitive. Versioned IDs may be accepted as `id@version` when multiple versions are registered.

## Validate a Delivery Profile

Use a profile only after it appears in `nvidia_usd_validate --help`. For example, if the active environment registers `Prop-Robotics-Neutral`, validate it explicitly:

```bash
nvidia_usd_validate --profile Prop-Robotics-Neutral examples/python/minimal/assets/sample_prop.usda
```

For automation or agent workflows, always write JSON:

```bash
nvidia_usd_validate --profile Prop-Robotics-Neutral --json-output reports/sample_prop.validation.json examples/python/minimal/assets/sample_prop.usda
```

Useful variants:

```bash
nvidia_usd_validate --profile Prop-Robotics-Neutral --csv-output reports/sample_prop.validation.csv examples/python/minimal/assets/sample_prop.usda
nvidia_usd_validate --profile Prop-Robotics-Neutral --group-by requirement examples/python/minimal/assets/sample_prop.usda
nvidia_usd_validate --profile Prop-Robotics-Neutral --predicate IsFailure examples/python/minimal/assets/sample_prop.usda
```

If no explicit scope is passed and profiles are registered, the CLI may auto-detect matching and non-matching profiles. For CI and delivery workflows, pass the required `--profile` so the result is deterministic.

If no profile is registered yet, run a base validation smoke test without `--profile`:

```bash
nvidia_usd_validate --json-output reports/sample_prop.validation.json examples/python/minimal/assets/sample_prop.usda
```

## Validation Hierarchy

Use this hierarchy when deciding what scope to run:

- Requirement: the smallest compliance claim, identified by a code and version.
- Rule: Python checker that validates one or more requirements and reports issues.
- Feature/capability: user-facing group of requirements for a capability of an asset.
- Profile: delivery target that groups capabilities, such as `Prop-Robotics-Neutral`.
- Plugin package: Python distribution that registers extra rules, requirements, features, capabilities, or profiles through entry points.

Prefer the broadest scope that matches the user's intent:

- Use `--profile` for delivery compliance.
- Use `--feature` or `--capability` when testing a known subset.
- Use `--requirement` to reproduce one compliance failure.
- Use `--rule` or `--category` for checker development and debugging.

## Narrow a Failure

When a profile fails, first read the JSON report with `skills/reading-json-output/SKILLS.md`. Then rerun a narrower scope only if you need a faster edit loop:

```bash
nvidia_usd_validate --requirement VG.010 examples/python/minimal/assets/sample_prop.usda
nvidia_usd_validate --rule TypeChecker examples/python/minimal/assets/sample_prop.usda
nvidia_usd_validate --category Geometry examples/python/minimal/assets/sample_prop.usda
```

The valid requirement/rule/category names must come from `--help` in the active environment. Do not invent names from memory.

## Explain Rules

Use `--explain` with selected rules or categories to print rule descriptions:

```bash
nvidia_usd_validate --category Geometry --explain examples/python/minimal/assets/sample_prop.usda
nvidia_usd_validate --rule TypeChecker --explain examples/python/minimal/assets/sample_prop.usda
```

## Key Commands

| Command | Purpose |
|---------|---------|
| `nvidia_usd_validate --help` | Show registered scopes in the active environment |
| `nvidia_usd_validate --profile PROFILE asset.usd` | Run delivery profile validation |
| `nvidia_usd_validate --json-output report.json ...` | Write structured JSON for agents and CI |
| `nvidia_usd_validate --csv-output report.csv ...` | Write tabular report for review |
| `nvidia_usd_validate --predicate IsFailure ...` | Filter output to failures |
| `nvidia_usd_validate --group-by requirement ...` | Group console output by requirement |
| `nvidia_usd_validate --fix ...` | Apply available automatic fixes |

## Common Pitfalls

- Running the CLI from a different environment than the one prepared for validation.
- Relying on profile auto-detection in CI instead of passing the required profile.
- Treating profile names, feature IDs, requirement codes, category names, or rule names as stable without checking `--help`.
- Reading console logs only when `--json-output` is available.
- Hiding failures with `--disable-feature` or narrowed scopes when the user asked for profile compliance.
- Using `--fix` on source assets before reviewing suggestions or working in a writable copy.
