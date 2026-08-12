---
name: validate-references
license: Apache-2.0 AND CC-BY-4.0
description: "Create USD Validation features with RequirementRef and feature dependencies. Do NOT use for authoring new requirements."
metadata:
  version: "1.20.0"
  author: "NVIDIA <info@nvidia.com>"
  tags:
    - usd-validation
    - features
    - requirements
    - references
compatibility: "Requires Python 3.10-3.14, uv or pip, network access to Python package indexes, and Linux/macOS shell or Windows PowerShell command syntax."
---

<!-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved. -->
<!-- SPDX-License-Identifier: Apache-2.0 AND CC-BY-4.0 -->

# Validate References

## Purpose

`usd-validation-nvidia` features can reference requirements and depend on features that are owned and implemented by
another installed validation package. This skill shows the smallest useful plugin that generates:

- one feature containing a `RequirementRef` to a built-in `com.nvidia.usd` requirement
- one feature that depends on that first feature

The referenced package supplies the concrete requirement object and rule; the downstream plugin supplies only the
generated feature composition.

## Prerequisites

- Python 3.10-3.14.
- `uv` or `pip` with package-index access.
- The package that implements the referenced requirements must be installed in the same environment as the feature
  plugin.

## Project Structure

```text
my-usd-validation-plugin/
  pyproject.toml
  main.py
  specs/
    features/
      ex_001.md
      ex_002.md
```

Use `validation/examples/python/validate-references` as the working example for this pattern.

## Verify Python Version

This skill requires Python 3.10-3.14. Before setup, run `uv run --python 3.11 python --version` or
`py -3.11 --version` on Windows; use `3.10`, `3.12`, `3.13`, or `3.14` instead if that is the supported interpreter. If no supported
interpreter is available, stop with: "This skill requires Python 3.10-3.14. Install a supported interpreter, then
rerun." For uv workflows, install one with `uv python install 3.11`.

## Setup with uv (Recommended)

Start from a clean parent directory outside this workspace where `my-usd-validation-plugin` does not already exist. If
that folder already exists, choose a different folder name or move the existing folder aside before continuing.

```bash
mkdir -p my-usd-validation-plugin && cd my-usd-validation-plugin
uv init --no-workspace --python 3.11
uv add "usd-validation-nvidia[usd]>=1.20.0"
```

Declare the plugin entry point and generated package force-include in `pyproject.toml`:

```toml
[project.entry-points."usd_validation_nvidia"]
my_plugin = "main:Plugin"

[tool.hatch.build.targets.wheel.force-include]
"example_validate_references" = "example_validate_references"
```

## Setup with pip

```bash
pip install "usd-validation-nvidia[usd]>=1.20.0"
pip install -e .
```

## Examples

### Minimal Reference Features

> **Source:** `validation/examples/python/validate-references/pyproject.toml`
>
> **Source:** `validation/examples/python/validate-references/specs/features/ex_001.md`
>
> Followed by: `validation/examples/python/validate-references/specs/features/ex_002.md`

The feature spec references `com.nvidia.usd.HI.004@1.0.0`, which is implemented by the built-in `DefaultPrimChecker`.
The dependent feature declares `Dependencies | ex_001 @ 1.0.0`, so selecting `com.example.usd.ex_002` also evaluates
the requirement referenced by `com.example.usd.ex_001`. It also references built-in `com.nvidia.usd.UN.001@1.0.0`
directly so the generated dependent feature is concrete; that requirement passes on the example asset.

Use the in-repo `profiles/` member (`--with ./profiles`) so generated features preserve external
requirement references and feature dependencies as reference objects (requires usd-profiles-nvidia >= 1.16.0;
the in-repo member satisfies this).

### Generate

From the repository root:

```bash
uv run \
  --no-project \
  --with ./profiles \
  python -m usd_profiles_nvidia.codegen \
    --docs-root validation/examples/python/validate-references/specs \
    --destination-dir validation/examples/python/validate-references \
    --package-name example_validate_references \
    --reverse-domain com.example.usd
```

On Windows:

```powershell
uv run `
  --no-project `
  --with ./profiles `
  python -m usd_profiles_nvidia.codegen `
    --docs-root validation/examples/python/validate-references/specs `
    --destination-dir validation/examples/python/validate-references `
    --package-name example_validate_references `
    --reverse-domain com.example.usd
```

The example package force-includes `example_validate_references`, so skipping this step fails during wheel build.

### Minimal main.py

> **Source:** `validation/examples/python/validate-references/main.py` snippet `referenced-features`
>
> Followed by: `validation/examples/python/validate-references/main.py` snippet `plugin-entry-point`
>
> **Asset:** `validation/examples/assets/asset-missing-default-prim.usda`

Import the generated `Features` enum and register both generated features with `register_features(...)`; unregister them
during shutdown. Do not register a new rule when another installed package already implements the referenced
requirement.

### Run

From the repository root, run the example feature to see the referenced built-in requirement fail:

This example requires `usd-validation-nvidia>=1.20.0`, which resolves generated `RequirementRef` objects to the
registered concrete requirements. If validation fails with `AttributeError: 'RequirementRef' object has no attribute
'parameters'`, the environment is using an older build.

```bash
uv run \
  --with ./validation \
  --with validation/examples/python/validate-references \
  nvidia_usd_validate --feature com.example.usd.ex_002 validation/examples/assets/asset-missing-default-prim.usda
```

This failure run is expected to exit non-zero and report `com.nvidia.usd.HI.004`, even though validation selected
`com.example.usd.ex_002`, because `ex_002` depends on `ex_001`. The direct `UN.001` reference in `ex_002` passes on
the example asset.

On Windows:

```powershell
uv run `
  --with ./validation `
  --with validation/examples/python/validate-references `
  nvidia_usd_validate --feature com.example.usd.ex_002 validation/examples/assets/asset-missing-default-prim.usda
```

## Key Types / Functions

- `RequirementRef(code=..., version=...)`: references a requirement by code/version without owning or re-declaring it.
- Feature dependency metadata (`Dependencies | ex_001 @ 1.0.0`): generates a feature dependency reference so one
  feature can preclude another.
- `Features.<NAME>`: generated feature enum value imported by the plugin.
- `register_features(...)`: registers the feature so `--feature` and profile composition can select it.
- `unregister_features(...)`: removes the feature on plugin shutdown.

## Key Dependencies

| Package | Purpose |
|---------|---------|
| `usd-validation-nvidia[usd]>=1.20.0` | Engine, CLI, plugin discovery, built-in `com.nvidia.usd` requirements, and OpenUSD runtime |
| `usd-profiles-nvidia` | Codegen package for generated feature DTOs |

## Limitations

- Covers feature composition with existing requirements and features only; use `validate-requirements` when authoring
  new requirement Markdown and rule mappings.
- Referenced requirements and dependent features must be registered by an installed package before validation runs.

## Common Pitfalls

- Generate the feature package before installing or running the plugin.
- Use the full requirement code, for example `com.nvidia.usd.HI.004`, when referencing requirements from another
  package.
- Keep generated reference versions aligned with installed requirement and feature versions, or omit versions only when
  latest compatible resolution is intended.
- Install the feature plugin into the same environment as the package that owns the referenced requirement.
- Register dependent local features together; selecting `ex_002` cannot resolve `ex_001` unless both are registered.
- Do not register duplicate rules for requirements already implemented by another package unless intentionally
  overriding the requirement validator.
- Confirm the feature appears in `nvidia_usd_validate --help` before debugging rule execution.

## Troubleshooting

- If `--feature` does not list the feature, confirm the plugin entry point uses the `usd_validation_nvidia` group and
  the plugin package is installed in the run environment.
- If building the plugin fails because `example_validate_references` is missing, run feature codegen before installing or
  building the example plugin.
- If validation reports "Requirement (...) has not been implemented" or a feature cannot be resolved, confirm the
  package that owns the referenced object is installed and that the code/version match exactly.
