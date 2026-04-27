# material-attributes

| Code          | NVM.001                              |
|---------------|--------------------------------------|
| Version       | 1.0.0                               |
| Validator     | {oav-validator-latest-link}`nvm-001` |
| Compatibility | {compatibility}`rtx`                 |
| Tags          | {tag}`essential`                    |

## Summary

Materials must specify additional "non-visual" material attributes

## Description

Materials bound to geometry prims with computed purpose "render" or "default" must have non-visual material attributes assigned to specify additional properties that affect non-visual sensor response.

## Why is it required?

- NVIDIA RTX requires these attributes to simulate non-visual sensors
- Special material properties affect sensor behavior. Attributes are spectrally dependent behavior that define how the a base substrate material is composited or layered with additional data driving response functions.
- Required for accurate simulation of retroreflective surfaces
- Needed for single-sided or transparent materials

## Examples

### Invalid: No attributes specified

```usd
#usda 1.0

def Material "BadMaterial" (
    prepend apiSchemas = ["MaterialBindingAPI"]
)
{
    token omni:simready:nonvisual:base = "aluminum"
    token omni:simready:nonvisual:coating = "clearcoat"
}
```

### Valid: Attributes specified

```usd
#usda 1.0

def Material "GoodMaterial" (
    prepend apiSchemas = ["MaterialBindingAPI"]
)
{
    token omni:simready:nonvisual:base = "aluminum"
    token omni:simready:nonvisual:coating = "clearcoat"
    token[] omni:simready:nonvisual:attributes = ["retroreflective", "single_sided"]
}
```

## How to comply

- Set omni:simready:nonvisual:attributes on materials
- Use valid attribute types:
  - none
  - emissive
  - retroreflective
  - single_sided
  - visually_transparent