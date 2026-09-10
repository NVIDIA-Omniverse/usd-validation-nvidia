# Profiles

A profile is the validation contract that a pipeline selects for an asset. It combines one or more features, and those
features resolve to requirements and rules.

For a factory workflow, a profile is useful because the asset must satisfy both general asset-quality expectations and
local assembly constraints. The example profile enables a customer feature named `factory_bounds`; that feature
depends on the built-in Minimal Placeable Visual feature and adds a factory-specific bounding-box requirement.

## Concept Map

- A requirement is one testable statement, such as "boundable prims must fit within a 6 m by 6 m by 4 m box."
- A capability groups related requirements, such as factory geometry requirements.
- A feature selects requirements and can depend on other features.
- A profile selects the features that define the complete validation target.

## Versioned TOML Profile

Use `profiles/profiles.toml` when a profile needs explicit versions:

```{eval-rst}
.. literalinclude:: ../examples/factory-bounds/specs/profiles/profiles.toml
   :language: toml
```

Feature entries are required by default. Add `optional = true` when a profile should use a feature only if that feature
is available in the runtime registry.

```toml
[Factory-Asset]
"1.1.0" = {features = [
    {"factory_bounds" = {version = "1.0.0"}},
    {"experimental_robotics_metadata" = {version = "0.1.0"}, optional = true},
]}
```

## Feature Dependencies

The profile above lists only the customer feature:

```text
{"factory_bounds" = {version = "1.0.0"}}
```

The customer feature is where Minimal Placeable Visual belongs in `dependencies`:

```markdown
| Dependencies | com.nvidia.usd.minimal_placeable_visual@1.0.0 |
```

That keeps the profile small and lets the feature remain the reusable unit. When the plugin registers generated
features and profiles, `ValidationEngine.enable_profile(...)` resolves the profile feature, the feature's dependencies,
and all referenced requirements.

## Runtime Parameter Overrides

Requirement default values are part of the generated package. A production line can override them from the CLI:

```bash
nvidia_usd_validate \
  --profile com.example.factory.Factory-Asset \
  --parameter MAX_X_METERS=4.0 \
  --parameter MAX_Y_METERS=3.0 \
  --parameter MAX_Z_METERS=2.5 \
  path/to/factory_prop.usda
```

The same can be done from Python:

```python
import factory_asset_profiles
from usd_validation_nvidia import UserParameter, ValidationEngine

engine = ValidationEngine()
engine.enable_profile(factory_asset_profiles.Profiles.FACTORY_ASSET)

max_x = engine.parameters["MAX_X_METERS"]
engine.add_parameter(UserParameter(parameter=max_x, assigned_value=4.0))

results = engine.validate("path/to/factory_prop.usda")
```

Use a new requirement version when a different default value should become part of the named profile contract.
