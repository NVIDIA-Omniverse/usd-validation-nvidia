# Capabilities

A capability groups related requirements by domain. Capabilities keep the authored specs navigable and give generated
packages a structured way to expose requirements.

For the factory bounding-box example, the capability is `Factory Geometry`: a local geometry policy that can grow over
time without changing the profile structure.

## File Structure

Place the capability Markdown file beside its requirement files:

```text
specs/
  capabilities/
    factory_geometry/
      capability-factory_geometry.md
      requirements/
        factory-boundable-size.md
```

The capability parser discovers requirement files below the `requirements/` directory and the `requirements-table`
directive renders them in documentation.

## Capability Markdown

```{eval-rst}
.. literalinclude:: ../examples/factory-bounds/specs/capabilities/factory_geometry/capability-factory_geometry.md
   :language: md
```

## Generated Python

After code generation, the capability and its requirements are available from the generated package:

```python
from factory_asset_profiles import Capabilities

capability = Capabilities.FACTORY_GEOMETRY
for requirement in capability.requirements:
    print(requirement.code, requirement.message)
```
