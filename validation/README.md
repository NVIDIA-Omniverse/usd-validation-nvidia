# USD Validation NVIDIA

An extensible framework to validate [OpenUSD](https://openusd.org) assets.
Inspired by Pixar's [usdchecker](https://graphics.pixar.com/usd/release/toolset.html#usdchecker),
this library extends validation capabilities with additional rules and provides automatic issue fixing.

It is the standalone successor to [`omniverse-asset-validator`](https://pypi.org/project/omniverse-asset-validator/) and is intended for use in any USD pipeline.

## Features

- Rule-based validation — Modular rule interface with registration mechanism for custom validators
- Flexible engine — Run validation on a `Usd.Stage`, individual layers, or recursively search folders
- Auto-fixing — Issue fixing interface for applying automated corrections when rules provide suggestions
- Command line interface — Standalone CLI for validation outside of GUI applications
- Lightweight — Pure Python implementation requiring only OpenUSD

## Installation

Install from PyPI:

```bash
pip install usd-validation-nvidia
```

## Optional Dependencies

For full functionality, install with optional dependencies:

```bash
# Include usd-core
pip install usd-validation-nvidia[usd]

# Include NumPy (for optimizations)
pip install usd-validation-nvidia[numpy]

# Install all optional dependencies
pip install usd-validation-nvidia[usd,numpy]
```

## Repository Layout and Releases

This repository is the single source repository for the shared NSPECT release and publishes
two Python packages from the same commit, both versioned from the shared `VERSION.md`:

- `usd-validation-nvidia` — the validation engine (source under `validation/src/`, with package docs,
  examples, and tests under `validation/`)
- `usd-profiles-nvidia` — profile/spec definitions and code generation tooling (`profiles/`
  directory, a `uv` workspace member; formerly a standalone repository)

`uv build --all-packages` produces wheels and sdists for both packages.

## Build from Source

Generate the capabilities package with the in-repo `profiles/` member (`usd-profiles-nvidia`), then build the wheel:

```bash
uv run \
  --no-project \
  --with ./profiles \
  python -m usd_profiles_nvidia.codegen \
    --docs-root specs \
    --destination-dir validation/src \
    --package-name usd_validation_nvidia.capabilities \
    --reverse-domain com.nvidia.usd

uv build --all-packages -o dist
```

## Basic usage

```python
from usd_validation_nvidia import ValidationEngine, IssueFixer

engine = ValidationEngine()
asset = "path/to/asset.usda"
results = engine.validate(asset)

for issue in results.issues():
    print(f"{issue.severity}: {issue.message}")

fixer = IssueFixer(asset)
fix_results = fixer.fix(results.issues())

for result in fix_results:
    print(f"{result.status}: {result.issue.message}")

fixer.save()
```

The `ValidationEngine` also supports selecting specific rules with `enable_rule()` / `disable_rule()`.
To filter by category in Python, enable the rules returned by `CategoryRuleRegistry().get_rules(category)`.

## Command Line Interface

The `nvidia_usd_validate` command provides validation from the terminal:

```bash
# Validate a single file
nvidia_usd_validate asset.usda

# Validate a directory recursively
nvidia_usd_validate ./assets/

# Apply automatic fixes
nvidia_usd_validate --fix asset.usda

# Validate specific categories
nvidia_usd_validate --category Material --category Geometry asset.usda

# Enable specific rules only
nvidia_usd_validate --no-init-rules --rule StageMetadataChecker asset.usda

# Export results to CSV
nvidia_usd_validate --csv-output results.csv asset.usda

# Show help
nvidia_usd_validate --help
```

## Documentation

- [Full Documentation](https://nvidia-omniverse.github.io/usd-validation-nvidia/)
- [API Reference](https://nvidia-omniverse.github.io/usd-validation-nvidia/validation/docs/api.html)
- [Available Rules](https://nvidia-omniverse.github.io/usd-validation-nvidia/validation/docs/rules.html)

## Requirements

- Python 3.10 - 3.13 with OpenUSD 23.11 or later
- Python 3.14 with OpenUSD 26.08

## License

Apache-2.0 AND CC-BY-4.0

## AI Coding Agents

The [AGENTS.md](https://github.com/NVIDIA-Omniverse/usd-validation-nvidia/blob/main/AGENTS.md) file and
[.agents/skills](https://github.com/NVIDIA-Omniverse/usd-validation-nvidia/tree/main/.agents/skills) directory contain
structured guidance for AI coding agents. Start there for Python project setup, local venv setup, and generated
requirement validation workflows.
