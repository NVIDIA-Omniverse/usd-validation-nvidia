---
name: validate-requirements
version: "1.19.0"
license: Apache-2.0
description: "Author and validate USD Validation requirements: Markdown specs, codegen, rule mapping, --requirement CLI. Do NOT use for basic plugins."
metadata:
  author: NVIDIA
  tags:
    - usd-validation
    - requirements
    - codegen
compatibility: "Requires Python 3.10-3.12, uv or pip, network access to Python package indexes, and Linux/macOS shell or Windows PowerShell command syntax."
---

<!-- SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved. -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Validate Requirements

## Purpose

`usd-validation-nvidia` extensions are Python plugin packages discovered through entry points.
This skill shows the smallest useful plugin that registers one rule backed by one requirement.
The requirement is authored as Markdown and generated with `usd-profiles-nvidia`, falling back to
`omniverse-usd-profiles` if needed; the rule registration, execution, and CLI filtering stay in `usd-validation-nvidia`.

## Prerequisites

- Python 3.10-3.12.
- `uv` or `pip` with package-index access.

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
  --with usd-profiles-nvidia \
  python -m usd_profiles_nvidia.codegen \
    --docs-root examples/python/requirement/specs \
    --destination-dir examples/python/requirement \
    --namespace example_requirements
```

If `usd-profiles-nvidia` is unavailable, use the legacy package:

```bash
uv run \
  --no-project \
  --with omniverse-usd-profiles \
  python -m omni.usd_profiles.codegen \
    --docs-root examples/python/requirement/specs \
    --destination-dir examples/python/requirement \
    --package-name example_requirements
```

On Windows:

```powershell
uv run `
  --no-project `
  --with usd-profiles-nvidia `
  python -m usd_profiles_nvidia.codegen `
    --docs-root examples/python/requirement/specs `
    --destination-dir examples/python/requirement `
    --namespace example_requirements
```

If `usd-profiles-nvidia` is unavailable on Windows, use the legacy package:

```powershell
uv run `
  --no-project `
  --with omniverse-usd-profiles `
  python -m omni.usd_profiles.codegen `
    --docs-root examples/python/requirement/specs `
    --destination-dir examples/python/requirement `
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
  --with usd-profiles-nvidia \
  python -m usd_profiles_nvidia.codegen \
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
  --with usd-profiles-nvidia `
  python -m usd_profiles_nvidia.codegen `
    --docs-root specs `
    --destination-dir src `
    --namespace usd_validation_nvidia.capabilities
uv run `
  --with . `
  --with examples/python/requirement `
  nvidia_usd_validate --requirement EXAMPLE.001 examples/assets/asset.usda
```

To see the requirement-mapped failure on Windows:

```powershell
uv run `
  --with . `
  --with examples/python/requirement `
  nvidia_usd_validate --requirement EXAMPLE.001 examples/assets/asset-missing-default-prim.usda
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
| `usd-profiles-nvidia` | Codegen package for generated requirements |
| `omniverse-usd-profiles` | Legacy codegen package for package-index fallback |

## Limitations

- Covers requirement-backed plugins only; use `project-setup-python` for basic custom rule plugins.
- Does not author full production capability models beyond the minimal example.

## Common Pitfalls

- Install the plugin package into the same environment as `usd-validation-nvidia`.
- Use the `usd_validation_nvidia` entry-point group for new plugins.
- In a fresh source checkout, generate `src/usd_validation_nvidia/capabilities` with `uv run --no-project --with
  usd-profiles-nvidia python -m usd_profiles_nvidia.codegen ...` before commands that install the local repo
  with `--with .`.
- Generate `example_requirements` before installing or running the example plugin.
- Requirements must live under a capability; an otherwise minimal capability Markdown file is enough for this example.
- Register requirements and rules in `on_startup()`, and unregister them in `on_shutdown()`.
- Pass the same requirement object to `register_requirements(...)` and `_AddFailedCheck(requirement=...)`.
- Confirm the requirement appears in `nvidia_usd_validate --help` before debugging rule behavior.

## Troubleshooting

- If installing or running the example fails because `example_requirements` is missing, run requirement codegen before
  building or installing the example plugin.
- If `--requirement EXAMPLE.001` does not select the custom rule, confirm the requirement package is generated,
  installed with the plugin, and registered from `on_startup()`.
