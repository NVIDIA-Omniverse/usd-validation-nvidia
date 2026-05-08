---
name: running-validation
description: Install and run NVIDIA USD Validation for OpenUSD assets. Use when validating USD/USDZ assets, installing the engine/profiles/validators packages, validating against profiles such as Prop-Robotics-Neutral, interpreting JSON output, applying fixes, or adding validation to CI.
---

# Running NVIDIA USD Validation

## Overview

Use this skill to set up the validation environment, run `nvidia_usd_validate`, scope validation to a profile/feature/capability/requirement/rule, parse JSON output, and map common failures to asset fixes.

## Install

Install the engine, USD support, optional NumPy acceleration, profiles, and extra validators into the same Python environment:

```bash
python -m pip install "usd-validation-nvidia[usd,numpy]" nvidia-usd-profiles nvidia-usd-validators
```

Notes:

- This repository's Python distribution is `usd-validation-nvidia` and its CLI is `nvidia_usd_validate`.
- Some product planning and package-index docs may refer to the engine family as `nvidia-usd-validation`; prefer the package name exposed by the target package index.
- Profiles such as `Prop-Robotics-Neutral` come from profile packages. If the profile is missing from CLI help, install or fix the profile package in the same environment.

## Discover Available Validation Scope

Run help after installation:

```bash
nvidia_usd_validate --help
```

The help text lists valid choices for:

- `--profile` / `--enable-profile`
- `--disable-profile`
- `--feature` / `--enable-feature`
- `--disable-feature`
- `--capability`
- `--requirement`
- `--category`
- `--rule`

Treat names as case-sensitive. Profile IDs may also be accepted as `id@version` when multiple versions are installed.

## Validation Hierarchy

Use this mental model when deciding what to run and how to read failures:

- Requirement: the smallest compliance claim, identified by a code and version.
- Rule: Python checker that validates one or more requirements and reports issues.
- Feature: user-facing group of requirements for a capability of an asset.
- Capability: broader requirement group used by generated profiles and engine scoping.
- Profile: delivery target that groups capabilities/features, such as `Prop-Robotics-Neutral`.
- Plugin package: Python distribution that registers extra rules, requirements, features, capabilities, or profiles through entry points.

Prefer `--profile` for delivery checks, then use the JSON `profiles[].features[].requirements[]` tree to understand which requirements blocked the profile.

## Validate Against Prop-Robotics-Neutral

Use an explicit profile for deterministic automation:

```bash
nvidia_usd_validate --profile Prop-Robotics-Neutral --json-output validation.json path/to/asset.usd
```

Useful variants:

```bash
nvidia_usd_validate --profile Prop-Robotics-Neutral --group-by requirement path/to/asset.usd
nvidia_usd_validate --profile Prop-Robotics-Neutral --predicate IsFailure path/to/asset.usd
nvidia_usd_validate --profile Prop-Robotics-Neutral --json-output validation.json --csv-output validation.csv path/to/asset.usd
```

If no explicit scope is passed and profiles are installed, the CLI may auto-detect matching and non-matching profiles. For CI and repeatable delivery checks, always pass `--profile`.

## Install Additional Entry Points

Profiles and validators are ordinary Python packages. To make their entry points visible, install them into the same active environment as `usd-validation-nvidia`:

```bash
python -m pip install nvidia-usd-profiles nvidia-usd-validators
nvidia_usd_validate --help
```

If a package installs successfully but its profiles or rules do not appear in `--help`, check the environment, package metadata, entry-point group, and import-time errors.

## Interpret JSON Output

`--json-output` writes a top-level object with:

- `status`: `PASS` if no issues were found, otherwise `FAIL`.
- `profiles`: profile, feature/capability, and requirement status when profile validation is active.
- `features`: feature/capability status when validation is scoped outside a profile.
- `rules`: rule-level results and issues.
- `issues[].severity`: `ERROR`, `FAILURE`, `WARNING`, or `INFO`.
- `issues[].requirement.code`: requirement code when the rule is tied to a requirement.
- `issues[].at`: location such as a prim path, property path, layer, stage, or schema.
- `issues[].suggestions`: available automatic fixes, when a rule provides them.

Triage order:

1. Handle `ERROR` first. These usually mean runtime/tooling problems such as unreadable assets, missing USD plugins/resources, or an exception in a validator.
2. Group `FAILURE` by `requirement.code` and `at.path`; these are compliance failures that block the selected scope.
3. Review `WARNING` as quality, performance, or incomplete-validation guidance.
4. Use `suggestions` to decide whether automatic fixing is safe.
5. Re-run the exact same profile after edits and compare the JSON.

## Common Fix Patterns

- Missing default prim: author a valid `defaultPrim` on the root layer.
- Wrong units or up axis: set stage metadata such as meters-per-unit and up-axis to the profile's expected values.
- Unresolved references or payloads: fix asset paths, package layout, resolver context, or missing files.
- Non-portable asset paths: make referenced paths relative and package-friendly.
- Missing extents or bad bounds: author or recompute extents for boundable prims.
- Mesh topology failures: repair invalid faces, duplicate vertices, zero-area faces, non-manifold edges, invalid normals, or bad primvar indexing.
- Material scope failures: move materials under accepted material scopes and fix material bindings.
- UsdPreviewSurface failures: fix shader input/output types, unsupported connections, invalid token values, or missing shader definitions in the USD runtime.
- USDZ failures: remove unsupported external dependencies and ensure packaged assets resolve inside the archive.

## Automatic Fixes

Use `--fix` only in a writable working copy or controlled authoring pipeline:

```bash
nvidia_usd_validate --profile Prop-Robotics-Neutral --fix path/to/asset.usd
```

Not every issue has a suggestion. If the JSON has no suggestion for an issue, edit the asset manually and re-run validation.

## CI Integration

Minimal CI shape:

```bash
python -m pip install "usd-validation-nvidia[usd,numpy]" nvidia-usd-profiles nvidia-usd-validators
nvidia_usd_validate --profile Prop-Robotics-Neutral --json-output validation.json path/to/asset.usd
```

Guidelines:

- Let the CLI exit code fail the job when issues are found.
- Upload `validation.json` as a build artifact.
- Avoid `--fix` in validation-only CI.
- Validate the exact profile required by the delivery target rather than relying on auto-detection.

## Common Pitfalls

- Installing profiles or validators into a different Python environment than the engine.
- Assuming `Prop-Robotics-Neutral` is built into the engine package. It is provided by a profile package.
- Reading only console logs when JSON output is available.
- Treating `WARNING` as a delivery failure without checking local policy.
- Hiding failures with `--disable-feature` or narrowed scopes when the user asked for profile compliance.
