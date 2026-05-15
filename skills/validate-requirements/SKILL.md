---
# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
name: validate-requirements
version: "1.0.0"
description: "Author and validate USD Validation requirements: Markdown specs, codegen, rule mapping, --requirement CLI. Do NOT use for basic plugins."
metadata:
  author: NVIDIA
  tags:
    - usd-validation
    - requirements
    - codegen
---

# Validate Requirements

## Overview

`usd-validation-nvidia` extensions are Python plugin packages discovered through entry points.
This skill shows the smallest useful plugin that registers one rule backed by one requirement.
The requirement is authored as Markdown and generated with `omniverse-usd-profiles` until `usd-profiles-nvidia` is
published; the rule registration, execution, and CLI filtering stay in `usd-validation-nvidia`.

## Project Structure

```text
my-usd-validation-plugin/
  pyproject.toml
  main.py
  specs/
    capabilities/
      capability-example.md
      requirements/
        default-prim.md
```

After `uv init`, create `main.py`, `specs/`, and the Markdown spec files manually or copy them from the example.

## Setup with uv (Recommended)

```bash
mkdir my-usd-validation-plugin && cd my-usd-validation-plugin
uv init --python 3.11
uv add "usd-validation-nvidia[usd]"
```

Declare the plugin entry point in `pyproject.toml`:

```toml
[project.entry-points."usd_validation_nvidia"]
my_plugin = "main:Plugin"
```

## Setup with pip

```bash
pip install "usd-validation-nvidia[usd]"
pip install -e .
```

## Minimal Requirement

> **Source:** `examples/python/requirement/pyproject.toml`
>
> **Source:** `examples/python/requirement/specs/capabilities/requirements/default-prim.md`
>
> Followed by: `examples/python/requirement/specs/capabilities/capability-example.md`

### Generate

From the repository root:

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

The example package force-includes `example_requirements`, so skipping this step fails during wheel build.

## Minimal main.py

> **Source:** `examples/python/requirement/main.py` snippet `custom-requirement`
>
> Followed by: `examples/python/requirement/main.py` snippet `custom-rule`
>
> Followed by: `examples/python/requirement/main.py` snippet `plugin-entry-point`
>
> **Asset:** `examples/assets/asset.usda`

Use `requirement=...` when reporting the issue so `--requirement` filtering can connect the rule failure back to the
generated requirement.

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
uv run \
  --with . \
  --with examples/python/requirement \
  nvidia_usd_validate --requirement EXAMPLE.001 examples/assets/asset.usda
```

To see the requirement-mapped failure:

```bash
uv run \
  --with . \
  --with examples/python/requirement \
  nvidia_usd_validate --requirement EXAMPLE.001 examples/assets/asset-missing-default-prim.usda
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
  --with examples\python\requirement `
  nvidia_usd_validate --requirement EXAMPLE.001 examples\assets\asset.usda
```

To see the requirement-mapped failure on Windows:

```powershell
uv run `
  --with . `
  --with examples\python\requirement `
  nvidia_usd_validate --requirement EXAMPLE.001 examples\assets\asset-missing-default-prim.usda
```

Note: replace `--with .` with `--with usd-validation-nvidia` to use the public build.

## Key Types / Functions

- `register_rule("Example")`: registers the rule in the `Example` category; the string argument is the rule category
  shown by the CLI.
- `register_requirements(...)`: maps a rule class to one or more generated requirements so `--requirement` filtering and
  reports can connect failures back to requirement IDs.
- `_AddFailedCheck(requirement=...)`: reports a validation failure associated with a generated requirement.

## Key Dependencies

| Package | Purpose |
|---------|---------|
| `usd-validation-nvidia[usd]` | Engine, CLI, plugin discovery, and `usd-core` runtime dependency |
| `omniverse-usd-profiles` | Current codegen package for generated requirements |
| `usd-profiles-nvidia` | Intended future codegen package name |

## Common Pitfalls

- Install the plugin package into the same environment as `usd-validation-nvidia`.
- Use the `usd_validation_nvidia` entry-point group for new plugins.
- In a fresh source checkout, generate `src/usd_validation_nvidia/capabilities` with `uv run --no-project --with
  omniverse-usd-profiles python -m omni.usd_profiles.codegen ...` before commands that install the local repo with
  `--with .`.
- Generate `example_requirements` before installing or running the example plugin.
- Requirements must live under a capability; an otherwise minimal capability Markdown file is enough for this example.
- Register requirements and rules in `on_startup()`, and unregister them in `on_shutdown()`.
- Pass the same requirement object to `register_requirements(...)` and `_AddFailedCheck(requirement=...)`.
- Confirm the requirement appears in `nvidia_usd_validate --help` before debugging rule behavior.
