# material-binding

| Code          | NVM.004                    |
|---------------|----------------------------|
| Version       | 1.0.0                     |
| Validator     |                            |
| Compatibility | {compatibility}`rtx`       |
| Tags          | {tag}`correctness`        |

## Summary

Attributes must be on bound materials

## Description

Non-visual material attributes must be authored on materials that are bound to geometry with material purpose "full". Attributes cannot be authored directly on geometry prims.

## Why is it required?

- Ensures consistent material property inheritance
- Maintains relationship between visual and non-visual attributes
- Enables material reuse across multiple geometries

## Examples

### Invalid: Attributes on geometry

```usd
#usda 1.0

def Mesh "BadGeometry" (
)
{
    token omni:simready:nonvisual:base = "aluminum"
    token omni:simready:nonvisual:coating = "clearcoat"
}
```

### Valid: Attributes on bound material

```usd
#usda 1.0

def Material "AluminumMaterial" (
    prepend apiSchemas = ["MaterialBindingAPI"]
)
{
    token omni:simready:nonvisual:base = "aluminum"
    token omni:simready:nonvisual:coating = "clearcoat"
}

def Mesh "GoodGeometry" (
    prepend apiSchemas = ["MaterialBindingAPI"]
)
{
    rel material:binding:full = </Materials/AluminumMaterial>
}
```

## How to comply

- Author non-visual material attributes on material prims, not on geometry
