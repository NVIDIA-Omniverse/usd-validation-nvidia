# usdgeom-extent

| Code          | VG.002                              |
|---------------|-------------------------------------|
| Version       | 1.0.0                               |
| Validator     | {oav-validator-latest-link}`vg-002` |
| Compatibility | {compatibility}`OpenUSD`            |
| Tags          | {tag}`performance`                  |

## Summary

Boundable geometry primitives should have valid extent values.

## Description

The extent of a geometry primitive represents its bounding box in local space.
For time-varying geometry, the extent must be computed at each time sample where the geometry changes, but should only be authored when it differs from the previous time sample's extent to minimize data storage.

## Why is it required?
- Enables rendering performance through efficient culling
- Enables fast spatial queries and collision detection
- Supports efficient scene traversal and bounding box calculations
- Provides accurate bounds for time-varying geometry

## Examples

### Valid: Extent that matches the geometry

```usd
#usda 1.0

def Mesh "MeshWithExtent"
{
    point3f[] points = [(0, 0, 0), (1, 1, 1)]
    float3[] extent = [(0, 0, 0), (1, 1, 1)]
}
```

### Invalid: Incorrect extent on static geometry

```usd
#usda 1.0

def Mesh "MeshWithIncorrectExtent" {
    point3f[] points = [(0,0,0), (1,1,1)]
    float3[] extent = [(-1,-1,-1), (1,1,1)]
}
```

### Invalid: Missing extent on time-varying geometry

```usd
#usda 1.0

def Mesh "MeshWithoutExtent" {
    float[] times = [0, 1]
    point3f[] points.timeSamples = {
        0: [(0,0,0), (1,1,1)],
        1: [(0,0,0), (2,2,2)]
    }
    # Missing extent attribute
}
```

### Valid: Extent authored only when it changes

```usd
#usda 1.0

def Mesh "MeshWithExtent" {
    float[] times = [0, 1]
    point3f[] points.timeSamples = {
        0: [(0,0,0), (1,1,1)],
        1: [(0,0,0), (2,2,2)]
    }
    float3[] extent.timeSamples = {
        0: [(0,0,0), (1,1,1)],  # Initial extent
        1: [(0,0,0), (2,2,2)]   # Extent changes with geometry
    }
}
```

### Invalid: Missing extent on curves

```usd
#usda 1.0

def BasisCurves "CurvesWithoutExtent"
{
    uniform token type = "linear"
    int[] curveVertexCounts = [2]
    point3f[] points = [(0, 0, 0), (1, 0, 0)]
    float[] widths = [1, 1]
}
```

### Invalid: Incorrect extent at several times

```usd
#usda 1.0

def Mesh "MeshWithIncorrectExtents"
{
    point3f[] points.timeSamples = {
        1: [(0, 0, 0), (1, 1, 1)],
        2: [(0, 0, 0), (2, 2, 2)]
    }
    # The extent is wrong at both times
    float3[] extent.timeSamples = {
        1: [(0, 0, 0), (5, 5, 5)],
        2: [(0, 0, 0), (5, 5, 5)]
    }
}
```

### Invalid: Incorrect extent at one time

```usd
#usda 1.0

def Points "PointsWithIncorrectExtent"
{
    point3f[] points.timeSamples = {
        1: [(0, 0, 0), (1, 0, 0)],
        2: [(0, 0, 0), (2, 0, 0)]
    }
    float[] widths.timeSamples = {
        1: [2, 2],
        2: [2, 2]
    }
    # The extent is correct at time 1 but was not updated at time 2
    float3[] extent.timeSamples = {
        1: [(-1, -1, -1), (2, 1, 1)],
        2: [(-1, -1, -1), (2, 1, 1)]
    }
}
```

### Invalid: Incorrect extent after the widths change

```usd
#usda 1.0

def Points "PointsWithChangingWidths"
{
    point3f[] points = [(0, 0, 0), (1, 0, 0)]
    float[] widths.timeSamples = {
        1: [2, 2],
        2: [4, 4]
    }
    # The extent is correct at time 1 but was not updated when the widths grew at time 2
    float3[] extent.timeSamples = {
        1: [(-1, -1, -1), (2, 1, 1)],
        2: [(-1, -1, -1), (2, 1, 1)]
    }
}
```

## How to comply
- Author extent for boundable geometry
- For time-varying geometry:
  - Compute extent at each time sample of attributes which may influence the extent. See `ComputeExtent` and `ComputeExtentFromPlugins` in [UsdGeomBoundable](https://openusd.org/release/api/class_usd_geom_boundable.html) for more information.
  - Only author when value changes

## For More Information
- [UsdGeom Extent Documentation](https://openusd.org/release/api/class_usd_geom_boundable.html)
