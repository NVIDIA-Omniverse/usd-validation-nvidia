---
name: project-setup-python
description: Setting up a Python project that uses NVIDIA USD Validation. Use when creating a new validation project, installing usd-validation-nvidia with usd-profiles-nvidia profile tooling, scaffolding a pyproject.toml, creating a sample USD asset, or running the first validation.
---

# Project Setup (Python)

## Overview

NVIDIA USD Validation is distributed as a Python package with a CLI entry point. A useful project setup installs the validation package and, when profile authoring or generated profile data is needed, the profile framework package:

1. `usd-validation-nvidia` - validation engine, built-in validators, and `nvidia_usd_validate` CLI.
2. `usd-profiles-nvidia` - profile/capability/feature/requirement framework and code generation tools.

Custom profile packages generated with `usd-profiles-nvidia`, or any custom validation plugins, must be installed into the same environment as `usd-validation-nvidia` so the validation engine can discover their entry points.

## Project Structure

```text
my-usd-validation-app/
  pyproject.toml
  assets/
    sample_prop.usda
  reports/
  main.py
```

## Setup with uv (Recommended)

```bash
mkdir my-usd-validation-app
cd my-usd-validation-app
uv init --python 3.11
uv add "usd-validation-nvidia[usd,numpy]" usd-profiles-nvidia
```

The resulting `pyproject.toml` should include the validation engine and profile tooling together:

```toml
[project]
name = "my-usd-validation-app"
version = "0.1.0"
requires-python = ">=3.10,<3.13"
dependencies = [
    "usd-validation-nvidia[usd,numpy]",
    "usd-profiles-nvidia",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

If `usd-profiles-nvidia` cannot be found, configure the package index used by the target project. Do not substitute guessed package names.

## Setup with pip

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install "usd-validation-nvidia[usd,numpy]" usd-profiles-nvidia
```

## Minimal main.py

Use the minimal Python example as the starting point:

> **Source:** `examples/python/minimal/main.py`
>
> **Asset:** `examples/python/minimal/assets/sample_prop.usda`

Important snippets:

- `create-engine` - construct `ValidationEngine`.
- `enable-profile` - optionally enable a profile from `USD_VALIDATION_PROFILE`.
- `validate-asset` - run validation for the sample asset.
- `print-issues` - print a compact issue summary and return a process exit code.

The sample asset is intentionally tiny. It proves the validation toolchain runs; delivery-profile validation may require a richer asset depending on the profile.

Run it:

```bash
uv run python examples/python/minimal/main.py
# or:
python examples/python/minimal/main.py
```

To run the same example against a registered profile:

```bash
# Windows PowerShell:
$env:USD_VALIDATION_PROFILE = "Prop-Robotics-Neutral"
python examples/python/minimal/main.py

# Linux/macOS:
USD_VALIDATION_PROFILE=Prop-Robotics-Neutral python examples/python/minimal/main.py
```

Only set `USD_VALIDATION_PROFILE` after confirming the profile appears in `nvidia_usd_validate --help`.

## Confirm the Installation

Run the CLI help from the same environment where the packages were installed:

```bash
nvidia_usd_validate --help
```

Check for these signals:

- `--profile`, `--feature`, `--capability`, `--requirement`, `--category`, and `--rule` appear in help.
- Built-in validator categories and rules from `usd-validation-nvidia` appear.
- Any project-specific profiles appear under valid `--profile` choices after their generated profile package or plugin is installed.

If the CLI command is not on `PATH`, use the module form:

```bash
python -m usd_validation_nvidia --help
```

## First CLI Validation

Run validation and write machine-readable output:

```bash
mkdir reports
nvidia_usd_validate --json-output reports/sample_prop.validation.json examples/python/minimal/assets/sample_prop.usda
```

Interpret the result:

- Exit code `0` means the selected validation scope passed.
- Exit code `1` means validation ran and found failures, warnings selected by policy, or errors.
- A missing-profile argument error means the selected generated profile package or custom plugin is not installed or not discovered in this environment.
- The JSON report is the artifact to inspect or upload, even when the command exits non-zero.

If the project requires `Prop-Robotics-Neutral`, first confirm it appears in `nvidia_usd_validate --help`, then run:

```bash
nvidia_usd_validate --profile Prop-Robotics-Neutral --json-output reports/sample_prop.validation.json examples/python/minimal/assets/sample_prop.usda
```

## Key Dependencies

| Package | Purpose |
|---------|---------|
| `usd-validation-nvidia[usd]` | Engine, CLI, built-in validators, and `usd-core` runtime dependency |
| `usd-validation-nvidia[numpy]` | NumPy acceleration where supported |
| `usd-profiles-nvidia` | Profile/capability/feature/requirement parsing, modeling, Sphinx integration, and code generation |
| Generated profile package or custom plugin | Registered delivery profiles such as `Prop-Robotics-Neutral`, when required by the project |

## Common Pitfalls

- Installing generated profile packages or plugins into a different virtual environment than the engine.
- Assuming `Prop-Robotics-Neutral` is built into `usd-validation-nvidia`; confirm the project-specific profile package or plugin registers it.
- Running an old shell after installation and missing the `nvidia_usd_validate` console script on `PATH`.
- Treating a sample asset failure as setup failure. First confirm the profile is registered and JSON was written.
- Guessing profile IDs. Use `nvidia_usd_validate --help` in the target environment.
