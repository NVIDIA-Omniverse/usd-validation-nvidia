# material-time

| Code          | NVM.006                              |
|---------------|--------------------------------------|
| Version       | 1.0.0                               |
| Validator     | {oav-validator-latest-link}`nvm-006` |
| Compatibility | {compatibility}`rtx`                 |
| Tags          | {tag}`correctness`                   |

## Summary

Properties must not be time-varying

## Description

Non-visual material properties cannot be time-varying since they represent static material properties that affect sensor response.

## Why is it required?

- Material properties represent physical characteristics
- Time-varying properties not supported by sensor simulation
- Ensures consistent sensor response

## Examples

### Invalid: Time-varying properties

```usd
#usda 1.0

def Material "BadMaterial" (
    prepend apiSchemas = ["MaterialBindingAPI"]
)
{
    token omni:simready:nonvisual:base.timeSamples = {
        0: "aluminum",
        48: "steel"
    }
}
```

### Valid: Static properties

```usd
#usda 1.0

def Material "GoodMaterial" (
    prepend apiSchemas = ["MaterialBindingAPI"]
)
{
    token omni:simready:nonvisual:base = "aluminum"
    token omni:simready:nonvisual:coating = "clearcoat"
    token[] omni:simready:nonvisual:attributes = ["retroreflective"]
}
```

## How to comply

- Use constant values for all non-visual material properties
- Remove any time samples from properties
- Use separate materials if different properties are needed