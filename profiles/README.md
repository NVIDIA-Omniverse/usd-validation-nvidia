# USD Profiles NVIDIA

A framework for defining and managing [OpenUSD](https://openusd.org) asset profiles, capabilities, and requirements.
This library provides tools for parsing profile specifications from Markdown, generating Python code,
and integrating with Sphinx documentation.

## Features

- **Profile definitions** — Define capabilities, features, and requirements in structured Markdown
- **Code generation** — Generate Python enums and dataclasses from profile specifications
- **Sphinx integration** — Custom directives and roles for rendering profile documentation
- **Validation support** — Generate validation rules from requirement specifications
- **Extensible** — Modular architecture for custom profile components

## AI Agent Guidance

AI coding agents should start with [AGENTS.md](AGENTS.md) for package context, expectations, and common workflows,
together with the repository root `AGENTS.md`. Repository-level agent skills live in the root `.agents/skills/`.

The runnable minimal code generation example is in [examples/python/minimal/](examples/python/minimal/).

## Installation

Install from PyPI:

```bash
pip install usd-profiles-nvidia
```

For Sphinx integration (directives and roles for profile documentation), install the optional dependency:

```bash
pip install usd-profiles-nvidia[sphinx]
```

## Basic Usage

### Loading Authored Feature Descriptors

Load Markdown or SimReady-style JSON/TOML feature descriptors directly into public API
DTOs without resolving requirements against a runtime registry:

```python
from pathlib import Path

from usd_profiles_nvidia import SpecificationsLoader

specifications = SpecificationsLoader(
    features_roots=[Path("features")],
    reverse_domain="com.nvidia.simready",
).load()
```

Directories are searched recursively and deterministically by `FeaturesParser`. The loader
delegates each configured root to that parser, then prefixes requirement codes that do not
already start with `reverse_domain` as a separate enrichment step. Feature dependencies remain `FeatureRef`
objects, and additional JSON/TOML fields are available through `Feature.custom_data`.
Parsing alone preserves requirement codes exactly as authored.

### Code Generation

Generate Python code from profile specifications. Create a folder (e.g. `specs/`) with this structure and the
following files:

```
specs/
├── capabilities/
│   ├── capability-example.md
│   └── requirements/
│       └── single-root.md
├── features/
│   └── feature-example.md
└── profiles/
    └── profile-example.md
```

**specs/capabilities/requirements/single-root.md**

```markdown
# single-root

| Code          | REQ.001                   |
|---------------|---------------------------|
| Version       | 1.0.0                     |
| Compatibility | {compatibility}`OpenUSD`   |
| Validator     |                           |
| Tags          | {tag}`essential`          |

## Summary

USD stage must have a single root prim.

## Description

Every USD asset must contain one root prim from which all other prims descend.
```

**specs/capabilities/capability-example.md**

~~~markdown
# Example

## Overview

Minimal capability with one requirement.

## Requirements

```{requirements-table}
```
~~~

**specs/features/feature-example.md**

~~~markdown
# Example

| Property   | Value   |
|------------|---------|
| Version    | 1.0.0   |
| Dependency | OpenUSD |

## Description

Minimal feature with one requirement.

## Requirements

```{features-table}
REQ.001@1.0.0
```
~~~

**specs/profiles/profile-example.md**

```markdown
# Example

Minimal profile with one feature.

## Features

- [Example](../features/feature-example.md)
```

Then run:

```bash
python -m usd_profiles_nvidia.codegen --docs-root specs --destination-dir output --namespace mypackage.profiles
```

Generated code will be under `output/mypackage/profiles/`.

### USD Validation NVIDIA integration

Use the generated requirements and features with
[USD Validation NVIDIA](https://pypi.org/project/usd-validation-nvidia/).
Implement rule checkers and run validation as needed.

**Implement a rule** -- Register requirements and implement checks. For example, for the minimal example's single-root
requirement:

```python
import mypackage.profiles as cap
from usd_validation_nvidia import BaseRuleChecker, register_requirements

@register_requirements(cap.Requirements.REQ_001_V1_0_0)
class SingleRootChecker(BaseRuleChecker):
    """USD stage must have a single root prim."""

    def CheckStage(self, usdStage):
        roots = [p for p in usdStage.GetPseudoRoot().GetChildren() if p.IsValid()]
        if len(roots) != 1:
            self._AddFailedCheck(
                "Stage must have exactly one root prim.",
                requirement=cap.Requirements.REQ_001_V1_0_0,
            )
```

**Validate with the generated feature** — Enable the feature you generated and run the engine:

```python
import mypackage.profiles
import usd_validation_nvidia

engine = usd_validation_nvidia.ValidationEngine(init_rules=False)
engine.enable_feature(mypackage.profiles.Features.EXAMPLE)
results = engine.validate("path/to/asset.usd")
```

### Sphinx Integration

Add to your Sphinx `conf.py`:

```python
extensions = [
    "usd_profiles_nvidia.sphinx.ext",
]
```

Use directives in your documentation:

````markdown
```{requirements-table}
geometry/mesh-valid
geometry/mesh-normals
```

```{features-table}
geometry/feature-mesh
```
````

Use roles for inline tags and compatibility badges:

```markdown
{tag}`performance` - Display a tag badge
{compatibility}`omniverse` - Display a compatibility badge
```

## Documentation

- [Full Documentation](https://nvidia-omniverse.github.io/usd-validation-nvidia/)
- [Validation Requirements](https://nvidia-omniverse.github.io/usd-validation-nvidia/validation/docs/requirements.html)

## Requirements

Core package:

- Python 3.10 or later
- Jinja2 3.1.5 or later
- markdown-it-py 3.0.0 or later
- tomli 2.0.0 or later for Python versions earlier than 3.11

Optional Sphinx integration (`usd-profiles-nvidia[sphinx]`):

- Sphinx 7.2.6 or later
- myst-parser 4.0.0 or later

## License

Apache-2.0 AND CC-BY-4.0
