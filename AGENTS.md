# AGENTS.md - AI Agent Guide for USD Validation NVIDIA

This file gives AI coding agents the minimum context needed to work effectively with this repository. Use it as a starting map, then go to `skills/` for task-level validation guidance.

## What This Repo Is

`usd-validation-nvidia` is a Python validation engine for OpenUSD assets. It provides:

- A Python package under `src/usd_validation_nvidia/`
- A command line validator, `nvidia_usd_validate`
- Rule, requirement, capability, feature, and profile registries
- JSON and CSV reporting for automation
- Entry-point based plugin discovery for external rule/profile packages

The package is used with USD profile and validator packages such as `nvidia-usd-profiles` and `nvidia-usd-validators`. Those packages must be installed in the same Python environment as the engine so their entry points are discovered.

## Start Here

- Read `README.md` for package installation and basic CLI/API examples.
- Read `skills/README.md` to understand the skill format and available task guides.
- Use `nvidia_usd_validate --help` inside the target Python environment to discover the profiles, features, capabilities, requirements, categories, and rules actually registered there.

## Repo Layout

- `src/usd_validation_nvidia/` - Python package source
- `src/omni/asset_validator/` - compatibility namespace for legacy `omni.asset_validator` imports
- `specs/` - source Markdown specs for capabilities, features, and requirements
- `src/usd_validation_nvidia/capabilities/` - generated package from `specs/`; do not edit by hand
- `tests/` - unit and CLI tests
- `skills/` - task-oriented agent skills (`*/SKILLS.md`)
- `.claude/commands/` - repo-specific command notes for local agent workflows

## Common Workflows

### Generate Capabilities

Before testing or packaging from a clean checkout, generate the capabilities package:

```bash
./repo.sh usd_profiles_codegen
```

On Windows:

```powershell
.\repo.bat usd_profiles_codegen
```

### Build Wheel

```bash
./repo.sh usd_profiles_codegen
./repo.sh uv -- build -o dist
```

### Run Tests

```bash
./repo.sh test
```

On Windows:

```powershell
.\repo.bat test
```

### CI Shape

GitLab builds the wheel in `build-pip` by running:

```bash
./repo.sh usd_profiles_codegen
./repo.sh uv -- build -o dist
```

The `test-pip` job installs the built wheel with `usd-core` versions `23.11`, `24.05`, `25.05`, and `25.11`, with and without NumPy versions `1.24` and `2.2`, then runs:

```bash
python -m unittest discover -s tests
```

## Use Skills for Task-Specific Work

When a request maps to a known validation workflow, go directly to the relevant skill in `skills/`:

- Installing and running validation, profile checks, JSON output, common fixes, and CI integration: `skills/running-validation/SKILLS.md`
- Extending validation with custom rules and plugin entry points: `skills/extending-validation/SKILLS.md`

If multiple skills seem relevant, start with `skills/running-validation/SKILLS.md`, then layer in `skills/extending-validation/SKILLS.md` only when custom validators or profile packages are involved.

## Agent Expectations

- Prefer small, targeted edits over broad refactors unless requested.
- Do not edit generated files under `src/usd_validation_nvidia/capabilities/` directly. Update `specs/` and regenerate instead.
- Keep `README.md`, `AGENTS.md`, and `skills/` in sync when CLI flags, package names, profile behavior, or JSON output change.
- Preserve licensing headers in source files where present.
- Use `--json-output` for machine-readable validation results in automation.
- Treat profile names as case-sensitive and environment-dependent; verify available profiles with `nvidia_usd_validate --help`.
