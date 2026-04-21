# NVIDIA USD Validation

An extensible framework to validate [OpenUSD](https://openusd.org) assets.
Inspired by Pixar's [usdchecker](https://graphics.pixar.com/usd/release/toolset.html#usdchecker),
this library extends validation capabilities with additional rules and provides automatic issue fixing.

## Features

- Rule-based validation — Modular rule interface with registration mechanism for custom validators
- Flexible engine — Run validation on a `Usd.Stage`, individual layers, or recursively search folders
- Auto-fixing — Issue fixing interface for applying automated corrections when rules provide suggestions
- Command line interface — Standalone CLI for validation outside of GUI applications
- Lightweight — Pure Python implementation requiring only OpenUSD

## Installation

Install from PyPI:

```bash
pip install nvidia-usd-validation
```

## Optional Dependencies

For full functionality, install with optional dependencies:

```bash
# Include usd-core
pip install nvidia-usd-validation[usd]

# Include NumPy (for optimizations)
pip install nvidia-usd-validation[numpy]

# Install all optional dependencies
pip install nvidia-usd-validation[usd,numpy]
```

## Basic usage

```python
from nvidia_usd_validation.asset_validator import ValidationEngine, IssueFixer

engine = ValidationEngine()
results = engine.validate("path/to/asset.usda")

for issue in results.issues():
    print(f"{issue.severity}: {issue.message}")

fixer = IssueFixer()
fix_results = fixer.fix(results.issues())

for result in fix_results:
    print(f"{result.status}: {result.issue.message}")
```

The `ValidationEngine` also supports selecting specific rules with `enableRule()` / `disableRule()`
and filtering by category with `enableCategory()`.

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

- [Full Documentation](https://docs.omniverse.nvidia.com/kit/docs/asset-validator)
- [API Reference](https://docs.omniverse.nvidia.com/kit/docs/asset-validator/latest/source/python/docs/api.html)
- [Available Rules](https://docs.omniverse.nvidia.com/kit/docs/asset-validator/latest/source/python/docs/rules.html)

## Requirements

- Python 3.10 - 3.12
- OpenUSD 22.11 or later

## License

Apache-2.0
