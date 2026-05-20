---
name: project-venv-setup
version: "1.19.0"
license: Apache-2.0
description: "Use when setting up a local usd-validation-nvidia venv for builds, tests, or nvidia_usd_validate. Do NOT use for plugin scaffolding."
metadata:
  author: NVIDIA
  tags:
    - usd-validation
    - venv
    - build
    - test
compatibility: "Requires Python 3.10-3.12, pip and venv, network access to Python package indexes, and Linux/macOS shell or Windows PowerShell command syntax."
---

<!-- SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved. -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Project Virtual Environment Setup

## Purpose

`usd-validation-nvidia` can be built and tested from a plain Python virtual environment. This skill shows how to
create a local `.venv`, generate the capabilities package required by source builds, build the wheel, install that
wheel into the virtual environment, run the unit tests, and use the `nvidia_usd_validate` command.

## Prerequisites

- Python 3.10-3.12.
- `pip`, `venv`, and package-index access.

## Project Structure

```text
usd-validation-nvidia/
  .venv/
  dist/
  specs/
  src/
  tests/
```

Run these commands from the repository root. The generated `src/usd_validation_nvidia/capabilities/` package is an
ignored build prerequisite and must not be edited by hand.

## Verify Python Version

This skill requires Python 3.10-3.12. Before creating `.venv`, run `python3.11 --version` or `py -3.11 --version` on
Windows; use `3.10` or `3.12` instead if that is the supported interpreter. If no supported interpreter is available,
stop with: "This skill requires Python 3.10-3.12. Install a supported interpreter, then rerun."

## Setup with venv (Recommended)

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip build
python -m pip install usd-profiles-nvidia
```

On Windows:

```powershell
py -3.11 -m venv .venv
./.venv/Scripts/Activate.ps1
python -m pip install --upgrade pip build
python -m pip install usd-profiles-nvidia
```

If `usd-profiles-nvidia` is unavailable, use the legacy package:

```bash
python -m pip install omniverse-usd-profiles
```

## Build from Source

Generate the capabilities package, then build the wheel:

```bash
python -m usd_profiles_nvidia.codegen \
  --docs-root specs \
  --destination-dir src \
  --namespace usd_validation_nvidia.capabilities

python -m build --wheel --outdir dist
```

On Windows:

```powershell
python -m usd_profiles_nvidia.codegen `
  --docs-root specs `
  --destination-dir src `
  --namespace usd_validation_nvidia.capabilities

python -m build --wheel --outdir dist
```

If `usd-profiles-nvidia` is unavailable, use the legacy package:

```bash
python -m omni.usd_profiles.codegen \
  --docs-root specs \
  --destination-dir src \
  --namespace usd_validation_nvidia.capabilities

python -m build --wheel --outdir dist
```

If `usd-profiles-nvidia` is unavailable on Windows, use the legacy package:

```powershell
python -m omni.usd_profiles.codegen `
  --docs-root specs `
  --destination-dir src `
  --namespace usd_validation_nvidia.capabilities

python -m build --wheel --outdir dist
```

## Install Built Wheel

Install the built wheel into the virtual environment with the same OpenUSD and NumPy versions used by the CI smoke test:

```bash
wheel=$(ls -t dist/usd_validation_nvidia-*.whl | head -n 1)
python -m pip install "$wheel" "usd-core==25.11" "numpy==2.2"
```

On Windows:

```powershell
$wheel = (
  Get-ChildItem ./dist/usd_validation_nvidia-*.whl |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1
).FullName
python -m pip install $wheel usd-core==25.11 numpy==2.2
```

Use `python -m pip install --force-reinstall "$wheel"` after rebuilding if the virtual environment already has an older
local wheel installed.

## Run

Run the test suite against the installed wheel:

```bash
python -m unittest discover -s tests
```

On Windows:

```powershell
python -m unittest discover -s tests
```

Run the command line validator from the activated virtual environment:

```bash
nvidia_usd_validate --help
nvidia_usd_validate --no-init-rules --rule DefaultPrimChecker examples/assets/asset.usda
```

On Windows:

```powershell
nvidia_usd_validate --help
nvidia_usd_validate --no-init-rules --rule DefaultPrimChecker examples/assets/asset.usda
```

## Key Types / Functions

- `python -m venv .venv`: creates the local virtual environment.
- `python -m usd_profiles_nvidia.codegen`: generates `usd_validation_nvidia.capabilities` from `specs/`.
- `python -m omni.usd_profiles.codegen`: legacy compatibility codegen module.
- `python -m build --wheel --outdir dist`: builds the source tree into a wheel.
- `python -m unittest discover -s tests`: runs the repository test suite.
- `nvidia_usd_validate`: validates USD assets from the installed package's console script.

## Key Dependencies

| Package | Purpose |
|---------|---------|
| `build` | PEP 517 wheel build frontend for source builds inside the venv |
| `usd-profiles-nvidia` | Capability, feature, and requirement code generation package |
| `omniverse-usd-profiles` | Legacy codegen package for package-index fallback |
| `usd-core==25.11` | OpenUSD runtime dependency used by the CI wheel smoke test example |
| `numpy==2.2` | Optional NumPy dependency used by the CI wheel smoke test example |

## Limitations

- Sets up a local Python virtual environment only; it does not publish release artifacts.
- CI parity depends on testing the built wheel rather than importing the editable source tree.

## Common Pitfalls

- Use Python 3.10-3.12; the examples above prefer Python 3.11.
- Activate the virtual environment before installing build tools, generated-code dependencies, the wheel, or test
  dependencies.
- Generate `src/usd_validation_nvidia/capabilities` before building; skipping it causes hatchling to fail because a
  forced include is missing.
- Build and test against the wheel in `dist/` rather than the editable source tree when checking CI parity.
- Reinstall the wheel after rebuilding, otherwise `nvidia_usd_validate` may still run code from the previous build.
- Use a focused rule such as `DefaultPrimChecker` for CLI smoke tests; running the full default rule set can exercise
  optional OpenUSD shader resources that are environment-dependent.

## Troubleshooting

- If the wheel build fails because a forced include is missing, generate `src/usd_validation_nvidia/capabilities` before
  running `python -m build`.
- If `nvidia_usd_validate` still runs old code after a rebuild, reinstall the newest wheel from `dist/` in the active
  virtual environment.
