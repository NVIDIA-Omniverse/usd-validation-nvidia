# usdgeom-mesh-topology

| Code          | VG.014                              |
|---------------|-------------------------------------|
| Version       | 1.0.0                              |
| Validator     | {oav-validator-latest-link}`vg-014` |
| Compatibility | {compatibility}`Core USD`          |
| Tags          | {tag}`correctness`                 |

## Summary

Mesh topology must be valid

## Description

Mesh topology must be valid for proper rendering and simulation. Invalid topology includes incorrect face winding, degenerate faces, and invalid vertex indices.

## Why is it required?

- Ensures clean rendering without artifacts
- Improves simulation behavior
- Enables accurate collision detection

## Examples

### Valid: Time-varying topology

```usd
#usda 1.0

def Mesh "ValidTimeVaryingTopology"
{
    int[] faceVertexCounts.timeSamples = {
        0: [4],
        1: [4]
    }
    int[] faceVertexIndices.timeSamples = {
        0: [0, 1, 2, 3],
        1: [0, 1, 2, 3]
    }
    point3f[] points.timeSamples = {
        0: [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)],
        1: [(0, 0, 0), (2, 0, 0), (2, 2, 0), (0, 2, 0)]
    }
}
```

### Valid: Time samples that start after time 0

```usd
#usda 1.0

def Mesh "ValidLaterTimeSamples"
{
    int[] faceVertexCounts.timeSamples = {
        1: [4]
    }
    int[] faceVertexIndices.timeSamples = {
        1: [0, 1, 2, 3]
    }
    point3f[] points.timeSamples = {
        1: [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
    }
}
```

### Invalid: Degenerate faces and invalid indices

```usd
#usda 1.0

def Mesh "BadTopology" {
    int[] faceVertexCounts = [4, 3]
    int[] faceVertexIndices = [
        0, 0, 0, 0,  # Degenerate face (all vertices same)
        0, 1, 99     # Invalid index (99 > number of points)
    ]
    point3f[] points = [(0,0,0), (1,0,0)]
}
```

### Valid: Proper topology

```usd
#usda 1.0

def Mesh "GoodTopology" {
    int[] faceVertexCounts = [4, 3]
    int[] faceVertexIndices = [
        0, 1, 2, 3,  # Proper quad
        0, 1, 2      # Proper triangle
    ]
    point3f[] points = [(0,0,0), (1,0,0), (1,1,0), (0,1,0)]
}
```

### Invalid: Face vertex counts that do not match the indices

```usd
#usda 1.0

def Mesh "CountsDoNotMatchIndices"
{
    int[] faceVertexCounts = [4, 3]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
}
```

### Invalid: Missing face vertex index

```usd
#usda 1.0

def Mesh "MissingIndex"
{
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2]
    point3f[] points = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
}
```

### Invalid: Mesh without data

```usd
#usda 1.0

def Mesh "MeshWithoutData"
{

}
```

### Invalid: Time-varying counts that do not match the indices

```usd
#usda 1.0

def Mesh "TimeVaryingCounts"
{
    int[] faceVertexCounts.timeSamples = {
        0: [4],
        1: [4, 3]
    }
    int[] faceVertexIndices.timeSamples = {
        0: [0, 1, 2, 3],
        1: [0, 1, 2, 3]
    }
    point3f[] points = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
}
```

### Invalid: Time-varying topology with a missing index

```usd
#usda 1.0

def Mesh "TimeVaryingMissingIndex"
{
    int[] faceVertexCounts.timeSamples = {
        0: [4],
        1: [4]
    }
    int[] faceVertexIndices.timeSamples = {
        0: [0, 1, 2, 3],
        1: [0, 1, 2]
    }
    point3f[] points = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
}
```

### Invalid: Time-varying topology with a missing point

```usd
#usda 1.0

def Mesh "TimeVaryingMissingPoint"
{
    int[] faceVertexCounts.timeSamples = {
        0: [4],
        1: [4]
    }
    int[] faceVertexIndices.timeSamples = {
        0: [0, 1, 2, 3],
        1: [0, 1, 2, 3]
    }
    point3f[] points = [(0, 0, 0), (1, 0, 0), (1, 1, 0)]
}
```

### Invalid: Time-varying points and counts that do not match the indices

```usd
#usda 1.0

def Mesh "TimeVaryingPointsAndCounts"
{
    int[] faceVertexCounts.timeSamples = {
        0: [4],
        1: [4, 3]
    }
    int[] faceVertexIndices.timeSamples = {
        0: [0, 1, 2, 3],
        1: [0, 1, 2, 3]
    }
    point3f[] points.timeSamples = {
        0: [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)],
        1: [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
    }
}
```

## How to comply
- Fix topology in source application
- Verify vertex indices
- Check face winding order

## For More Information
- [UsdGeom Mesh Documentation](https://openusd.org/release/api/class_usd_geom_mesh.html)