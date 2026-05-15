---
# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
name: project-venv-setup
description: Creating a local Python venv for usd-validation-nvidia, generating capabilities, building the project from source, installing the built wheel into the venv, running tests against the wheel, or using the nvidia_usd_validate command from that environment.
---

# Project Virtual Environment Setup

## Overview

`usd-validation-nvidia` can be built and tested from a plain Python virtual environment. This skill shows how to
create a local `.venv`, generate the capabilities package required by source builds, build the wheel, install that
wheel into the virtual environment, run the unit tests, and use the `nvidia_usd_validate` command.

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

## Setup with venv (Recommended)

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip build
python -m pip install usd-profiles-nvidia==1.14.1
```

On Windows:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip build
python -m pip install usd-profiles-nvidia==1.14.1
```

If `usd-profiles-nvidia` is not available on the default index in an NVIDIA environment, install it from the same index
used by CI:

```bash
python -m pip install \
  --index-url https://urm.nvidia.com/artifactory/api/pypi/ct-omniverse-pypi-local/simple \
  usd-profiles-nvidia==1.14.1
```

## Setup with pip

Use `pip` inside the activated virtual environment for every dependency and install step. Avoid mixing packages from a
different Python environment with the local `.venv`.

```bash
python -m pip --version
python -c "import sys; print(sys.executable)"
```

## Build from Source

Generate the capabilities package, then build the wheel:

```bash
python -m usd_profiles_nvidia.codegen \
  --docs-root specs \
  --destination-dir src \
  --package-name usd_validation_nvidia.capabilities

python -m build --wheel --outdir dist
```

On Windows:

```powershell
python -m usd_profiles_nvidia.codegen `
  --docs-root specs `
  --destination-dir src `
  --package-name usd_validation_nvidia.capabilities

python -m build --wheel --outdir dist
```

## Run

Install the built wheel into the virtual environment with the same OpenUSD and NumPy versions used by the CI smoke test,
then run the test suite against the installed wheel:

```bash
wheel=$(ls -t dist/usd_validation_nvidia-*.whl | head -n 1)
python -m pip install "$wheel" "usd-core==25.11" "numpy==2.2"
python -m unittest discover -s tests
```

On Windows:

```powershell
$wheel = (
  Get-ChildItem .\dist\usd_validation_nvidia-*.whl |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1
).FullName
python -m pip install $wheel usd-core==25.11 numpy==2.2
python -m unittest discover -s tests
```

After installation, run the command line validator from the activated virtual environment:

```bash
nvidia_usd_validate --help
nvidia_usd_validate examples/assets/asset.usda
```

On Windows:

```powershell
nvidia_usd_validate --help
nvidia_usd_validate examples\assets\asset.usda
```

Use `python -m pip install --force-reinstall "$wheel"` after rebuilding if the virtual environment already has an older
local wheel installed.

## Key Types / Functions

- `python -m venv .venv`: creates the local virtual environment.
- `python -m usd_profiles_nvidia.codegen`: generates `usd_validation_nvidia.capabilities` from `specs/`.
- `python -m build --wheel --outdir dist`: builds the source tree into a wheel.
- `python -m unittest discover -s tests`: runs the repository test suite.
- `nvidia_usd_validate`: validates USD assets from the installed package's console script.

## Key Dependencies

| Package | Purpose |
|---------|---------|
| `build` | PEP 517 wheel build frontend for source builds inside the venv |
| `usd-profiles-nvidia==1.14.1` | Capability, feature, and requirement code generation used by README and CI builds |
| `usd-core==25.11` | OpenUSD runtime dependency used by the CI wheel smoke test example |
| `numpy==2.2` | Optional NumPy dependency used by the CI wheel smoke test example |

## Common Pitfalls

- Use Python 3.10-3.12; the examples above prefer Python 3.11.
- Activate the virtual environment before installing build tools, generated-code dependencies, the wheel, or test
  dependencies.
- Generate `src/usd_validation_nvidia/capabilities` before building; skipping it causes hatchling to fail because a
  forced include is missing.
- Build and test against the wheel in `dist/` rather than the editable source tree when checking CI parity.
- Reinstall the wheel after rebuilding, otherwise `nvidia_usd_validate` may still run code from the previous build.
- Confirm the command is coming from `.venv` with `python -c "import sys; print(sys.executable)"` when command discovery
  or dependency versions look wrong.
