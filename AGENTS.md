<!-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved. -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# AGENTS.md - AI Agent Guide for USD Validation NVIDIA

This file gives AI coding agents the minimum context needed to work effectively with this repository. Use it as a
starting map, then go to `skills/` for task-level validation guidance.

## What This Repo Is

`usd-validation-nvidia` is a Python validation engine for OpenUSD assets. It provides:

- A Python package under `src/usd_validation_nvidia/`
- A command line validator, `nvidia_usd_validate`
- Rule, requirement, capability, feature, and profile registries
- JSON and CSV reporting for automation
- Entry-point based plugin discovery for external rule/profile packages

The package contains the validation engine and built-in validators. It is commonly used with generated profile
definitions; profile packages or custom plugins must be installed in the same Python environment as the engine so their
entry points are discovered.

## Start Here

- Read `README.md` for package installation and basic CLI/API examples.
- Read `skills/README.md` to understand the skill format and available task guides.
- For agents that do not automatically load `skills/`, such as Claude in some setups or Codex CLI when skills are not
  auto-discovered, explicitly read `AGENTS.md`, `skills/README.md`, and then the relevant `skills/*/SKILLS.md` file
  before following a workflow.
- Use `nvidia_usd_validate --help` inside the target Python environment to discover the profiles, features,
  capabilities, requirements, categories, and rules actually registered there.

## Fresh Checkout Prerequisite

When running this repository from source with `--with .`, generate the ignored capabilities package first:

```bash
uv run \
  --no-project \
  --with omniverse-usd-profiles \
  python -m omni.usd_profiles.codegen \
    --docs-root specs \
    --destination-dir src \
    --namespace usd_validation_nvidia.capabilities
```

`usd-profiles-nvidia` is the intended package name once published. When it is available, use:

```bash
uv run \
  --no-project \
  --with usd-profiles-nvidia \
  python -m usd_profiles_nvidia.codegen \
    --docs-root specs \
    --destination-dir src \
    --package-name usd_validation_nvidia.capabilities
```

Published wheels already include `src/usd_validation_nvidia/capabilities`; fresh source checkouts do not. Skipping this
step causes a hatchling `Forced include not found: .../capabilities` error when building or installing the local source
with `--with .`.

## Repo Layout (High Level)

- `src/usd_validation_nvidia/` - Python package source
- `src/omni/asset_validator/` - compatibility namespace for legacy `omni.asset_validator` imports
- `specs/` - source Markdown specs for capabilities, features, and requirements
- `examples/` - runnable examples referenced by skill files
- `src/usd_validation_nvidia/capabilities/` - generated package from `specs/`; do not edit by hand
- `tests/` - unit and CLI tests
- `skills/` - task-oriented agent skills (`*/SKILLS.md`)

## Common Workflows

### Minimal Plugin Example

Install the repo and minimal plugin example into the run environment, then run the custom rule against the example
asset:

```bash
uv run \
  --with . \
  --with examples/python/minimal \
  nvidia_usd_validate --rule ExampleDefaultPrimChecker examples/assets/asset.usda
```

On Windows:

```powershell
uv run `
  --with . `
  --with examples\python\minimal `
  nvidia_usd_validate --rule ExampleDefaultPrimChecker examples\assets\asset.usda
```

### Requirement-Backed Plugin Example

Generate the example requirement package, then run the plugin with one custom requirement registered for CLI filtering
and JSON mapping:

```bash
uv run \
  --no-project \
  --with omniverse-usd-profiles \
  python -m omni.usd_profiles.codegen \
    --docs-root examples/python/requirement/specs \
    --destination-dir examples/python/requirement \
    --namespace example_requirements
```

`usd-profiles-nvidia` is the intended package name once published. When it is available, use:

```bash
uv run \
  --no-project \
  --with usd-profiles-nvidia \
  python -m usd_profiles_nvidia.codegen \
    --docs-root examples/python/requirement/specs \
    --destination-dir examples/python/requirement \
    --package-name example_requirements
```

On Windows:

```powershell
uv run `
  --no-project `
  --with omniverse-usd-profiles `
  python -m omni.usd_profiles.codegen `
    --docs-root examples\python\requirement\specs `
    --destination-dir examples\python\requirement `
    --namespace example_requirements
```

Future package name on Windows:

```powershell
uv run `
  --no-project `
  --with usd-profiles-nvidia `
  python -m usd_profiles_nvidia.codegen `
    --docs-root examples\python\requirement\specs `
    --destination-dir examples\python\requirement `
    --package-name example_requirements
```

After codegen, run the plugin:

```bash
uv run \
  --with . \
  --with examples/python/requirement \
  nvidia_usd_validate --requirement EXAMPLE.001 examples/assets/asset.usda
```

To see a requirement-mapped failure:

```bash
uv run \
  --with . \
  --with examples/python/requirement \
  nvidia_usd_validate --requirement EXAMPLE.001 examples/assets/asset-missing-default-prim.usda
```

On Windows:

```powershell
uv run `
  --with . `
  --with examples\python\requirement `
  nvidia_usd_validate --requirement EXAMPLE.001 examples\assets\asset.usda
```

To see a requirement-mapped failure on Windows:

```powershell
uv run `
  --with . `
  --with examples\python\requirement `
  nvidia_usd_validate --requirement EXAMPLE.001 examples\assets\asset-missing-default-prim.usda
```

### CLI Example

Discover registered validation scopes in the active environment:

```bash
uv run nvidia_usd_validate --help
```

Run a smoke validation and write JSON:

```bash
mkdir -p reports
uv run nvidia_usd_validate \
  --json-output reports/asset.validation.json \
  examples/assets/asset.usda
```

### Tests

For CI parity, build the wheel and run tests against the wheel rather than the editable source tree:

```bash
uv run \
  --no-project \
  --with omniverse-usd-profiles \
  python -m omni.usd_profiles.codegen \
    --docs-root specs \
    --destination-dir src \
    --namespace usd_validation_nvidia.capabilities
uv build -o dist
uv run \
  --no-project \
  --with ./dist/usd_validation_nvidia-*.whl \
  --with usd-core==25.11 \
  --with numpy==2.2 \
  python -m unittest discover -s tests
```

On Windows:

```powershell
uv run `
  --no-project `
  --with omniverse-usd-profiles `
  python -m omni.usd_profiles.codegen `
    --docs-root specs `
    --destination-dir src `
    --namespace usd_validation_nvidia.capabilities
uv build -o dist
$wheel = (Get-ChildItem .\dist\usd_validation_nvidia-*.whl | Select-Object -First 1).FullName
uv run `
  --no-project `
  --with $wheel `
  --with usd-core==25.11 `
  --with numpy==2.2 `
  python -m unittest discover -s tests
```

## Use Skills for Task-Specific Work

When a request maps to a known validation workflow, go directly to the relevant skill in `skills/`:

- Python setup and first sample validation: `skills/project-setup-python/SKILLS.md`
- Validate Requirements: `skills/validate-requirements/SKILLS.md`

If multiple skills seem relevant, start with the narrowest skill that matches the user request, then layer in adjacent
skills only when the workflow needs them.

## Agent Expectations

- Prefer small, targeted edits over broad refactors unless requested.
- Do not edit generated files under `src/usd_validation_nvidia/capabilities/` directly. Update `specs/` and
  regenerate instead.
- Keep `README.md`, `AGENTS.md`, and `skills/` in sync when CLI flags, package names, profile behavior, or JSON output
  change.
- Preserve licensing headers in source files where present.
- Use `--json-output` for machine-readable validation results in automation.
- Treat profile names as case-sensitive and environment-dependent; verify available profiles with
  `nvidia_usd_validate --help`.

## Notes

- The project is pre-release; behavior, APIs, and packaging details may evolve.
- `usd-profiles-nvidia` is the intended package for profile/capability code generation. If it is not available in the
  package registry yet, use the legacy `omniverse-usd-profiles` package and `omni.usd_profiles.codegen` module.
