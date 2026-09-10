# Features

A feature is a reusable validation unit. It selects one or more requirements and can depend on other features.

For the factory profile, the custom feature adds a bounding-box check while depending on the built-in Minimal Placeable
Visual feature. Enabling this one feature therefore enables both the factory dimensions and the baseline requirements
needed for a placeable visual asset.

## Metadata

Feature descriptors can be authored as TOML:

```toml
id = "factory_bounds"
version = "1.0.0"
dependencies = ["com.nvidia.usd.minimal_placeable_visual@1.0.0"]
```

Use fully-qualified IDs, such as `com.nvidia.usd.minimal_placeable_visual@1.0.0`, when dependencies belong to another
package. The validation engine resolves them from the registered features at runtime.

When authoring Markdown feature descriptors, the feature ID is derived from the filename. In TOML, set `id` explicitly.

## Requirements

List the requirements contributed by the feature with the `requirements` field:

```toml
requirements = ["GEOMETRY.001@1.0.0"]
```

Requirements from dependent features are not repeated in this list. The validation engine resolves them from the
feature's `dependencies` when the feature or a profile containing it is enabled.

## Configuration Pattern

The feature selects the parameterized requirement; the requirement supplies default values. Runtime callers can then
override those values:

```bash
nvidia_usd_validate \
  --feature com.example.factory.factory_bounds \
  --parameter MAX_X_METERS=4.0 \
  --parameter MAX_Y_METERS=3.0 \
  --parameter MAX_Z_METERS=2.5 \
  path/to/factory_prop.usda
```

When a factory needs a different default policy, create a new requirement version with different defaults and point a
new feature version at that requirement.

## Complete Example

```{eval-rst}
.. literalinclude:: ../examples/factory-bounds/specs/features/factory_bounds.toml
   :language: toml
```
