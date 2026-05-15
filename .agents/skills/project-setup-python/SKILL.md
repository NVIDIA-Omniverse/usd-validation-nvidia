---
# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
name: project-setup-python
version: "1.0.0"
description: "Set up Python NVIDIA USD Validation plugins: entry points, custom rules, uv/pip install, first CLI run. Do NOT use for requirements."
metadata:
  author: NVIDIA
  tags:
    - usd-validation
    - python
    - plugin-setup
---

# Project Setup and First Validation (Python)

## Purpose

`usd-validation-nvidia` is distributed as a Python package on PyPI. This skill shows how to scaffold a minimal plugin
project and run its first validation command.

## Project Structure

```text
my-usd-validation-plugin/
  pyproject.toml
  main.py
```

After `uv init`, create `main.py` and update `pyproject.toml` to match the structure below.

## Setup with uv (Recommended)

```bash
mkdir my-usd-validation-plugin && cd my-usd-validation-plugin
uv init --python 3.11
uv add "usd-validation-nvidia[usd]"
```

This creates a `pyproject.toml` and `uv.lock`. The minimal example uses:

```toml
[project]
name = "usd-validation-minimal-plugin"
version = "0.1.0"
description = "Minimal NVIDIA USD Validation plugin example"
requires-python = ">=3.10,<3.13"
dependencies = [
    "usd-validation-nvidia[usd]",
]

[project.entry-points."usd_validation_nvidia"]
minimal_example = "main:Plugin"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
only-include = ["main.py"]
```

### Adding optional dependencies

For NumPy acceleration:

```bash
uv add "usd-validation-nvidia[numpy]"
```

For profile code generation, use the legacy package until `usd-profiles-nvidia` is published:

```bash
uv add omniverse-usd-profiles
```

`usd-profiles-nvidia` is the intended package name once published:

```bash
uv add usd-profiles-nvidia
```

## Setup with pip

```bash
pip install "usd-validation-nvidia[usd]"
pip install -e .
```

## Minimal main.py

> **Source:** `examples/python/minimal/pyproject.toml`
>
> **Source:** `examples/python/minimal/main.py` snippet `custom-rule`
>
> Followed by: `examples/python/minimal/main.py` snippet `plugin-entry-point`
>
> **Asset:** `examples/assets/asset.usda`

### Run

From the repository root:

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

```bash
uv run \
  --with . \
  --with examples/python/minimal \
  nvidia_usd_validate --rule ExampleDefaultPrimChecker examples/assets/asset.usda
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
uv run `
  --with . `
  --with examples/python/minimal `
  nvidia_usd_validate --rule ExampleDefaultPrimChecker examples/assets/asset.usda
```

Note: replace `--with .` with `--with usd-validation-nvidia` to use the public build.

## Key Types / Functions

- `register_rule("Example")`: registers the rule in the `Example` category; the string argument is the rule category
  shown by the CLI.
- `BaseRuleChecker.CheckStage(...)`: validates the whole stage once.
- `_AddFailedCheck(...)`: reports a validation failure.

## Key Dependencies

| Package | Purpose |
|---------|---------|
| `usd-validation-nvidia[usd]` | Engine, CLI, built-in validators, and `usd-core` runtime dependency |
| `usd-validation-nvidia[numpy]` | Optional NumPy acceleration |
| `omniverse-usd-profiles` | Current profile codegen package used until `usd-profiles-nvidia` is published |
| `usd-profiles-nvidia` | Intended future profile/capability/feature/requirement modeling and code generation package |
| `usd-profiles-nvidia[sphinx]` | Optional Sphinx directives and roles for profile documentation |

## Common Pitfalls

- `usd-validation-nvidia` requires Python 3.10-3.12.
- Install the plugin package into the same environment as `usd-validation-nvidia`.
- In a fresh source checkout, generate `src/usd_validation_nvidia/capabilities` with `uv run --no-project --with
  omniverse-usd-profiles python -m omni.usd_profiles.codegen ...` before commands that install the local repo with
  `--with .`.
- Point the entry point at `main:Plugin` when the package exposes a `Plugin` class.
- Confirm the custom rule appears in `nvidia_usd_validate --help` before debugging validation output.
- Project-specific profiles such as `Prop-Robotics-Neutral` must be installed and registered before use.
