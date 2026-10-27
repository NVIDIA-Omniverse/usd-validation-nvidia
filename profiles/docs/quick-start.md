# Quick Start

`usd-profiles-nvidia` lets pipeline teams describe a validation contract as authored documentation, generate Python
objects from that same source, and use those objects with `usd-validation-nvidia`.

This guide creates a small profile package for a factory pipeline. The profile validates assets against the built-in
Minimal Placeable Visual feature and adds one custom requirement: every boundable prim must fit inside a configured
bounding-box size.

## Install

Install the profile tooling and validation engine:

```bash
pip install usd-profiles-nvidia usd-validation-nvidia
```

## Create a Specs Tree

Create a `specs/` directory in your profile package:

```text
specs/
  capabilities/
    factory_geometry/
      capability-factory_geometry.md
      requirements/
        factory-boundable-size.md
  features/
    factory_bounds.toml
  profiles/
    profiles.toml
```

## Author the Requirement

The requirement describes the policy and declares the values that the rule can read:

```{eval-rst}
.. literalinclude:: ../examples/factory-bounds/specs/capabilities/factory_geometry/requirements/factory-boundable-size.md
   :language: md
```

The `Default Value` column is the profile package's default configuration. At runtime, users can override those values
with `--parameter` or `ValidationEngine.add_parameter()`.

## Add a Capability

Capabilities group related requirements. This example creates a factory geometry capability:

```{eval-rst}
.. literalinclude:: ../examples/factory-bounds/specs/capabilities/factory_geometry/capability-factory_geometry.md
   :language: md
```

## Add a Feature

The feature depends on the built-in Minimal Placeable Visual feature and contributes the factory bounding-box
requirement:

```{eval-rst}
.. literalinclude:: ../examples/factory-bounds/specs/features/factory_bounds.toml
   :language: toml
```

Use the fully-qualified `com.nvidia.usd.minimal_placeable_visual@1.0.0` entry in `dependencies` so the generated package
keeps that reference external. The validation engine resolves it from the built-in `usd-validation-nvidia`
registrations.

## Add a Profile

The profile only needs to select the customer feature. That feature brings in Minimal Placeable Visual through
`dependencies`:

```{eval-rst}
.. literalinclude:: ../examples/factory-bounds/specs/profiles/profiles.toml
   :language: toml
```

## Generate Python

Generate Python objects from the authored specs:

```bash
python -m usd_profiles_nvidia.codegen \
  --docs-root specs \
  --destination-dir generated \
  --package-name factory_asset_profiles \
  --reverse-domain com.example.factory
```

The reverse domain qualifies local identifiers. For example, `GEOMETRY.001` becomes
`com.example.factory.GEOMETRY.001`, while `com.nvidia.usd.minimal_placeable_visual` remains an external feature
reference.

## Bind the Requirement to a Rule

Register the generated requirement, feature, and profile from a `usd_validation_nvidia` plugin:

```{eval-rst}
.. literalinclude:: ../examples/factory-bounds/factory_validation.py
   :language: python
```

Add the plugin entry point to your package:

```toml
[project.entry-points."usd_validation_nvidia"]
factory_validation = "factory_validation:Plugin"
```

## Validate Assets

Install the generated profile package and plugin into the same Python environment as `usd-validation-nvidia`, then
select the profile:

```bash
nvidia_usd_validate \
  --profile com.example.factory.Factory-Asset \
  path/to/factory_prop.usda
```

Override the default bounding-box limits for a specific factory line:

```bash
nvidia_usd_validate \
  --profile com.example.factory.Factory-Asset \
  --parameter MAX_X_METERS=4.0 \
  --parameter MAX_Y_METERS=3.0 \
  --parameter MAX_Z_METERS=2.5 \
  path/to/factory_prop.usda
```
