# USD Validation NVIDIA

`usd-validation-nvidia` is a repository for NVIDIA OpenUSD asset validation and
profile tooling. It contains an extensible validation engine, a command line
validator, and the profile/specification utilities used to describe OpenUSD
capabilities, features, and requirements.

The repository publishes two Python packages from the same commit, both
versioned from the shared [`VERSION.md`](VERSION.md):

- [`usd-validation-nvidia`](validation/README.md): A standalone validation
  framework for OpenUSD assets, including the `nvidia_usd_validate` CLI,
  built-in rule registries, JSON/CSV reporting, and automatic issue fixing.
- [`usd-profiles-nvidia`](profiles/README.md): Tooling for authoring profile
  specifications in Markdown, generating Python code, and integrating profile
  documentation with Sphinx.

## Repository Layout

- `validation/`: Validation package source, documentation, examples, and tests.
- `profiles/`: Profile/specification package source and code generation tools.
- `specs/`: Authored Markdown specifications for capabilities, features, and
  requirements used by the validation package.
- `.agents/skills/`: Task-oriented guidance for AI coding agents working in
  this repository.
- `AGENTS.md`: Repository-level guidance for AI coding agents.

## Installation

Install the released validation engine:

```bash
pip install usd-validation-nvidia
```

Install the released profile tooling:

```bash
pip install usd-profiles-nvidia
```

Optional extras are available for OpenUSD, NumPy, and Sphinx integrations. See
the package READMEs for details:

- [Validation package README](validation/README.md)
- [Profiles package README](profiles/README.md)

## Build From Source

Generate the validation capabilities package from the in-repository profile
tooling, then build all packages:

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

`uv build --all-packages` produces wheels and source distributions for both
`usd-validation-nvidia` and `usd-profiles-nvidia`.

## Basic Validation

After installing the validation package, run the CLI against a USD asset:

```bash
nvidia_usd_validate path/to/asset.usda
```

The validation engine can also be used from Python:

```python
from usd_validation_nvidia import ValidationEngine

engine = ValidationEngine()
results = engine.validate("path/to/asset.usda")

for issue in results.issues():
    print(f"{issue.severity}: {issue.message}")
```

## Documentation

- [Full Documentation](https://nvidia-omniverse.github.io/usd-validation-nvidia/)
- [Validation API Reference](https://nvidia-omniverse.github.io/usd-validation-nvidia/validation/docs/api.html)
- [Available Validation Rules](https://nvidia-omniverse.github.io/usd-validation-nvidia/validation/docs/rules.html)
- [Validation Requirements](https://nvidia-omniverse.github.io/usd-validation-nvidia/validation/docs/requirements.html)

## Requirements

- Python 3.10 - 3.12 for validation workflows (`usd-validation-nvidia`
  does not yet support Python 3.13+)
- OpenUSD 22.11 or later for validation workflows

## License

Apache-2.0 AND CC-BY-4.0
