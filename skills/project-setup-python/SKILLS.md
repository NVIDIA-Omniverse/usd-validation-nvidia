---
# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
name: project-setup-python
description: Setting up a Python plugin project that uses NVIDIA USD Validation. Use when creating a new validation project, wiring a usd_validation_nvidia entry point, registering a custom rule, installing the plugin with uv or pip, or running the first validation against a USD asset.
---

# Project Setup (Python)

## Overview

`usd-validation-nvidia` is distributed as a Python package on PyPI. This skill shows how to scaffold a minimal plugin project.

## Project Structure

```text
my-usd-validation-plugin/
  pyproject.toml
  main.py
```

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

For profile code generation:

```bash
uv add usd-profiles-nvidia
```

`usd-profiles-nvidia` is the intended package name. If it is not available in the package registry yet, use the legacy
package:

```bash
uv add omniverse-usd-profiles
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
  --with usd-profiles-nvidia \
  python -m usd_profiles_nvidia.codegen \
    --docs-root specs \
    --destination-dir src \
    --package-name usd_validation_nvidia.capabilities
```

If `usd-profiles-nvidia` is not available in the package registry yet, use the legacy PyPI package:

```bash
uv run \
  --no-project \
  --with omniverse-usd-profiles \
  python -m omni.usd_profiles.codegen \
    --docs-root specs \
    --destination-dir src \
    --namespace usd_validation_nvidia.capabilities
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
  --with usd-profiles-nvidia `
  python -m usd_profiles_nvidia.codegen `
    --docs-root specs `
    --destination-dir src `
    --package-name usd_validation_nvidia.capabilities
uv run `
  --with . `
  --with examples\python\minimal `
  nvidia_usd_validate --rule ExampleDefaultPrimChecker examples\assets\asset.usda
```

Note: replace `--with .` with `--with usd-validation-nvidia` to use the public build.

## Key Dependencies

| Package | Purpose |
|---------|---------|
| `usd-validation-nvidia[usd]` | Engine, CLI, built-in validators, and `usd-core` runtime dependency |
| `usd-validation-nvidia[numpy]` | Optional NumPy acceleration |
| `usd-profiles-nvidia` | Optional profile/capability/feature/requirement modeling and code generation |
| `omniverse-usd-profiles` | Legacy profile codegen package to use if `usd-profiles-nvidia` is not available yet |
| `usd-profiles-nvidia[sphinx]` | Optional Sphinx directives and roles for profile documentation |

## Common Pitfalls

- `usd-validation-nvidia` requires Python 3.10-3.12.
- Install the plugin package into the same environment as `usd-validation-nvidia`.
- In a fresh source checkout, generate `src/usd_validation_nvidia/capabilities` with `uv run --no-project --with
  usd-profiles-nvidia python -m usd_profiles_nvidia.codegen ...` before commands that install the local repo with
  `--with .`.
- Point the entry point at `main:Plugin` when the package exposes a `Plugin` class.
- Confirm the custom rule appears in `nvidia_usd_validate --help` before debugging validation output.
- Project-specific profiles such as `Prop-Robotics-Neutral` must be installed and registered before use.
