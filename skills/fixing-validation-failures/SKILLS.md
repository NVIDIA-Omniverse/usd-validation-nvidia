---
name: fixing-validation-failures
description: Fixing NVIDIA USD Validation failures in OpenUSD assets. Use when mapping validation issues to USD edits, deciding whether --fix is safe, repairing common profile failures, or rerunning validation after asset changes.
---

# Fixing Validation Failures

## Overview

Use this skill after a validation report exists. Read the JSON first with `skills/reading-json-output/SKILLS.md`, then choose targeted asset edits. Keep the validation scope unchanged while iterating so before/after reports are comparable.

## Fix Workflow

1. Run the required validation scope and write JSON. For delivery work, use the required profile after confirming it appears in `nvidia_usd_validate --help`:

   ```bash
   nvidia_usd_validate --profile REQUIRED_PROFILE --json-output reports/before.json asset.usd
   ```

2. Sort issues by severity:

   - `ERROR`: fix tool/runtime/input problems first.
   - `FAILURE`: fix compliance blockers.
   - `WARNING`: fix when local policy requires it or it indicates likely data quality problems.
   - `INFO`: informational only.

3. Group failures by `requirement.code`, `rule.name`, and `at.path`.
4. Apply the smallest USD edit that addresses the root cause.
5. Re-run the same command and save a new report:

   ```bash
   nvidia_usd_validate --profile REQUIRED_PROFILE --json-output reports/after.json asset.usd
   ```

## Automatic Fixes

Use `--fix` only in a writable working copy or controlled authoring pipeline:

```bash
nvidia_usd_validate --profile REQUIRED_PROFILE --fix asset.usd
```

Use JSON to decide whether automatic fixing is available:

- `suggestions[]` empty: edit manually.
- One or more `suggestions[]`: the rule can propose fixes.
- Multiple suggestions: inspect the messages and choose a safe workflow; the CLI fixer may use the default suggestion path.

Do not use `--fix` in validation-only CI.

## Common Fix Patterns

| Symptom | Typical fix |
|---------|-------------|
| Missing or invalid default prim | Author `defaultPrim` on the root layer and ensure the target prim exists |
| Wrong up axis or units | Set root-layer stage metadata such as `upAxis` and `metersPerUnit` to the profile expectation |
| Unresolved references or payloads | Fix asset paths, resolver context, package layout, or missing files |
| Non-portable asset paths | Make references relative or package-friendly |
| Missing extents or invalid bounds | Author or recompute extents for boundable prims |
| Mesh topology failures | Repair invalid faces, duplicate vertices, zero-area faces, non-manifold edges, invalid normals, or bad primvar indexing |
| Material scope or binding failures | Move materials under accepted scopes and repair material bindings |
| UsdPreviewSurface failures | Fix shader input/output types, unsupported connections, token values, or missing shader definitions |
| USDZ/package failures | Remove unsupported external dependencies and ensure packaged assets resolve inside the archive |

## Editing Metadata with Python

For simple stage metadata fixes, use USD APIs rather than string edits:

```python
from pxr import Usd, UsdGeom

stage = Usd.Stage.Open("asset.usda")
root = stage.GetPseudoRoot().GetLayer()

if not stage.GetDefaultPrim():
    prim = stage.GetPrimAtPath("/Root")
    if prim:
        stage.SetDefaultPrim(prim)

UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
UsdGeom.SetStageMetersPerUnit(stage, 1.0)
root.Save()
```

Adapt paths and values to the failing requirement and project policy.

## Fixing Resolver and Dependency Errors

If issues point to missing files, unresolved references, or package dependency failures:

1. Reproduce the failure from the same working directory and resolver context used by CI.
2. Confirm every referenced layer, payload, texture, MDL file, or external asset exists.
3. Prefer relative paths for portable assets.
4. For USDZ, ensure dependencies are inside the archive or allowed by the target profile.
5. Re-run validation after changing paths, not only after copying files.

## Verify the Fix

Use the exact same profile and output shape:

```bash
nvidia_usd_validate --profile REQUIRED_PROFILE --json-output reports/after.json asset.usd
```

Then confirm:

- Top-level `status` is now `PASS`, or the intended issue count decreased.
- The same `requirement.code` no longer appears as `FAIL`.
- No new `ERROR` entries were introduced.
- Any remaining `WARNING` entries are acceptable under local delivery policy.

## Common Pitfalls

- Fixing by disabling rules or features when the task asks for profile compliance.
- Editing USDA text directly when USD APIs would preserve layer structure more safely.
- Using `--fix` on source assets before reviewing the suggested edits.
- Treating a path copy as a fix without rerunning validation in the target resolver context.
- Changing profile/package versions between before and after reports.
