# material-consistency

| Code          | NVM.005                    |
|---------------|----------------------------|
| Version       | 1.0.0                     |
| Validator     |                            |
| Compatibility | {compatibility}`rtx`       |
| Tags          | {tag}`correctness`        |

## Summary

Properties must be consistent with visual materials

## Description

Non-visual material attributes must be consistent with the visual material attributes of the same material. The non-visual attributes should accurately represent the physical characteristics implied by the visual material.

## Why is it required?

- Ensures accurate sensor simulation
- Prevents conflicting material definitions
- Maintains physical plausibility

## Examples

### Invalid: Inconsistent attributes

```usd
#usda 1.0

def Material "GlassMaterial" (
    prepend apiSchemas = ["MaterialBindingAPI"]
)
{
    # Visual material shows glass
    token outputs:surface.connect = </Materials/GlassMaterial/PBRShader.outputs:surface>

    # But non-visual attributes say it's metal
    token omni:simready:nonvisual:base = "aluminum"
    token omni:simready:nonvisual:coating = "none"
}
```

### Valid: Consistent attributes

```usd
#usda 1.0

def Material "GlassMaterial" (
    prepend apiSchemas = ["MaterialBindingAPI"]
)
{
    # Visual material shows glass
    token outputs:surface.connect = </Materials/GlassMaterial/PBRShader.outputs:surface>

    # Non-visual attributes match
    token omni:simready:nonvisual:base = "clear_glass"
    token omni:simready:nonvisual:coating = "none"
    token[] omni:simready:nonvisual:attributes = ["visually_transparent"]
}
```

## How to comply

- Match non-visual attributes to visual appearance
- Include appropriate attributes (e.g., visually_transparent for glass)
- Ensure physical plausibility of material definitions