---
name: project-setup-python
license: Apache-2.0 AND CC-BY-4.0
description: "Set up Python NVIDIA USD Validation plugins: entry points, custom rules, uv/pip install, first CLI run. Do NOT use for requirements."
metadata:
  version: "1.19.1"
  author: "NVIDIA <info@nvidia.com>"
  tags:
    - usd-validation
    - python
    - plugin-setup
compatibility: "Requires Python 3.10-3.14, uv or pip, network access to Python package indexes, and Linux/macOS shell or Windows PowerShell command syntax."
---

<!-- SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved. -->
<!-- SPDX-License-Identifier: Apache-2.0 AND CC-BY-4.0 -->

# Project Setup and First Validation (Python)

## Purpose

`usd-validation-nvidia` is distributed as a Python package on PyPI. This skill shows how to scaffold a minimal plugin
project and run its first validation command.

## Prerequisites

- Python 3.10-3.14.
- `uv` or `pip` with package-index access.

## Project Structure

```text
my-usd-validation-plugin/
  pyproject.toml
  main.py
```

After `uv init`, create `main.py` and update `pyproject.toml` to match the structure below.

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
uv add "usd-validation-nvidia[usd]"
```

This creates a `pyproject.toml` and `uv.lock`. The minimal example uses:

```toml
[project]
name = "usd-validation-minimal-plugin"
version = "0.1.0"
description = "Minimal NVIDIA USD Validation plugin example"
requires-python = ">=3.10,<3.15"
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

For profile code generation, use the public package:

```bash
uv add usd-profiles-nvidia
```

## Setup with pip

```bash
pip install "usd-validation-nvidia[usd]"
pip install -e .
```

## Examples

### Minimal main.py

> **Source:** `validation/examples/python/minimal/pyproject.toml`
>
> **Source:** `validation/examples/python/minimal/main.py` snippet `custom-rule`
>
> Followed by: `validation/examples/python/minimal/main.py` snippet `plugin-entry-point`
>
> **Asset:** `validation/examples/assets/asset.usda`

### Run

From the repository root:

```bash
uv run \
  --no-project \
  --with ./profiles \
  python -m usd_profiles_nvidia.codegen \
    --docs-root specs \
    --destination-dir validation/src \
    --package-name usd_validation_nvidia.capabilities \
    --reverse-domain com.nvidia.usd
```

```bash
uv run \
  --with ./validation \
  --with validation/examples/python/minimal \
  nvidia_usd_validate --rule ExampleDefaultPrimChecker validation/examples/assets/asset.usda
```

On Windows:

```powershell
uv run `
  --no-project `
  --with ./profiles `
  python -m usd_profiles_nvidia.codegen `
    --docs-root specs `
    --destination-dir validation/src `
    --package-name usd_validation_nvidia.capabilities `
    --reverse-domain com.nvidia.usd
uv run `
  --with ./validation `
  --with validation/examples/python/minimal `
  nvidia_usd_validate --rule ExampleDefaultPrimChecker validation/examples/assets/asset.usda
```

Note: replace `--with ./validation` with `--with usd-validation-nvidia` to use the public build.

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
| `usd-profiles-nvidia` | Profile/capability/feature/requirement modeling and code generation package |
| `usd-profiles-nvidia[sphinx]` | Optional Sphinx directives and roles for profile documentation |

## Limitations

- Covers basic rule plugins only; use `validate-requirements` for requirement-backed workflows.
- Does not publish packages or configure external CI.

## Common Pitfalls

- `usd-validation-nvidia` requires Python 3.10-3.14. Python 3.14 requires OpenUSD 26.08 when installing the `[usd]` extra.
- Install the plugin package into the same environment as `usd-validation-nvidia`.
- In a fresh source checkout, generate `validation/src/usd_validation_nvidia/capabilities` with `uv run --no-project --with
  ./profiles python -m usd_profiles_nvidia.codegen ...` before commands that install the local repo
  with `--with ./validation`.
- Point the entry point at `main:Plugin` when the package exposes a `Plugin` class.
- Confirm the custom rule appears in `nvidia_usd_validate --help` before debugging validation output.
- Project-specific profiles such as `Prop-Robotics-Neutral` must be installed and registered before use.

## Troubleshooting

- If `nvidia_usd_validate --help` does not list the custom rule, confirm the plugin is installed in the same
  environment and the entry point targets `main:Plugin`.
- If local source installation fails because `capabilities` is missing, generate
  `validation/src/usd_validation_nvidia/capabilities` from `specs/` before using `--with ./validation`.
