# material-coating

| Code          | NVM.003                              |
|---------------|--------------------------------------|
| Version       | 1.0.0                               |
| Validator     | {oav-validator-latest-link}`nvm-003` |
| Compatibility | {compatibility}`rtx`                 |
| Tags          | {tag}`correctness`                   |

## Summary

Materials must specify surface coating

## Description

Materials bound to geometry prims with computed purpose "render" or "default" must have a non-visual material coating property assigned to specify any surface treatment that affects non-visual sensor response.

## Why is it required?

- Surface coatings modify sensor response characteristics
- Required for accurate sensor simulation by providing additional material variations that would otherwise be absent with just the base material.
- Affects reflection and absorption properties by treating the coatings as a layer deposited on the base material substrate.

## Examples

### Invalid: No coating specified

```usd
#usda 1.0

def Material "BadMaterial" (
    prepend apiSchemas = ["MaterialBindingAPI"]
)
{
    token omni:simready:nonvisual:base = "aluminum"
}
```

### Valid: Coating specified

```usd
#usda 1.0

def Material "GoodMaterial" (
    prepend apiSchemas = ["MaterialBindingAPI"]
)
{
    token omni:simready:nonvisual:base = "aluminum"
    token omni:simready:nonvisual:coating = "clearcoat"
}
```

## How to comply

- Set omni:simready:nonvisual:coating on materials
- Use valid coating types:
  - none
  - paint
  - clearcoat
  - paint_clearcoat