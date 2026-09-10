# factory-boundable-size

| Code          | GEOMETRY.001             |
|---------------|--------------------------|
| Version       | 1.0.0                    |
| Compatibility | {compatibility}`OpenUSD` |
| Validator     | FactoryBoundsChecker     |
| Tags          | {tag}`correctness`       |

## Summary

Factory assets must fit within the configured bounding-box dimensions.

## Description

The validator computes each boundable prim's world-space bounding box and compares its size to the configured factory
limits. The default values below describe the placement envelope for one factory line in meters.

## Parameters

| Parameter    | Type  | Default Value |
|--------------|-------|---------------|
| MAX_X_METERS | float | 6.0           |
| MAX_Y_METERS | float | 6.0           |
| MAX_Z_METERS | float | 4.0           |

## Why is it required?

- Prevents oversized assets from blocking automated placement.
- Catches unit-scale mistakes before assets reach assembly scenes.
- Keeps factory layout validation aligned with the physical production cell.

## Examples

### Invalid: oversized fixture

```usd
#usda 1.0
(
    metersPerUnit = 1
)

def Cube "OversizedFixture"
{
    double size = 8
}
```

### Valid: bounded fixture

```usd
#usda 1.0
(
    metersPerUnit = 1
)

def Cube "Fixture"
{
    double size = 2
}
```

## How to comply

- Confirm `metersPerUnit` matches the source asset's authored unit scale.
- Split large equipment into separately placed assets when the factory workflow expects modular props.
- Reduce unused geometry, collision, or visualization extents that inflate the computed bounding box.
