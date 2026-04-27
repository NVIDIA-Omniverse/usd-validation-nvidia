# usdgeom-zero-extent

| Code          | VG.030                              |
|---------------|-------------------------------------|
| Version       | 1.0.0                              |
| Validator     | {validator-latest-link}`scene-optimizer:vg-030` |
| Compatibility | {compatibility}`Core USD`          |
| Tags          | {tag}`performance`                 |

## Summary

Boundable geometry should have non-zero extents in at least one dimension.

## Description

Zero extent geometry wastes memory and may cause simulation problems.

## Why is it required?

- Memory inefficiency
- Rendering artifacts
- Physics simulation issues

## Examples

### Invalid: Zero extent

```usd
#usda 1.0

def Mesh "ZeroExtentMesh" {
    float3[] extent = [(0, 0, 0), (0, 0, 0)]
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [
        (0,0,0),
        (0,0,0),
        (0,0,0),
        (0,0,0)
    ]
}
```

### Valid: Mesh has nonzero extent

```usd
#usda 1.0

def Mesh "NonzeroExtentMesh" {
    float3[] extent = [(0, 0, 0), (1, 1, 0)]
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [
        (0,0,0),
        (1,0,0),
        (1,1,0),
        (0,1,0)
    ]
}
```

## How to comply
- Remove zero extent geometry from scene
- Fix geometry generation settings

## For More Information
- [UsdGeom Boundable Documentation](https://openusd.org/release/api/class_usd_geom_boundable.html)
