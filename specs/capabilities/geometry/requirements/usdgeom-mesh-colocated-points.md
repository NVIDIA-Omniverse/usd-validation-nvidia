# usdgeom-mesh-colocated-points

| Code          | VG.016                              |
|---------------|-------------------------------------|
| Version       | 1.0.0                              |
| Validator     | {validator-latest-link}`scene-optimizer:vg-016` |
| Compatibility | {compatibility}`Core USD`          |
| Tags          | {tag}`performance`                 |

## Summary

Each vertex position should be unique

## Description

Each vertex position should be unique. Multiple vertices at the same position (co-located points) waste memory and can cause rendering artifacts.

## Why is it required?
- Improves memory efficiency
- Prevents potential shading issues
- Avoids physics simulation issues
- Smaller file sizes

## Examples

### Invalid: Co-located points

```usd
#usda 1.0

def Mesh "MeshWithColocatedPoints" {
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [
        (1,1,1),  # Point 0
        (1,1,1),  # Point 1 - same as Point 0
        (2,2,2),
        (3,3,3)
    ]
}
```

### Valid: No co-located points

```usd
#usda 1.0

def Mesh "CleanMesh" {
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 0, 1, 2]  # Reuse point 0 instead
    point3f[] points = [
        (1,1,1),
        (2,2,2),
        (3,3,3)
    ]
}
```

## How to comply
- Weld co-located vertices in Source Application
- Fix mesh generation settings
- Scene Optimizer - Merge Vertices

## For More Information
- [UsdGeom Mesh Documentation](https://openusd.org/release/api/class_usd_geom_mesh.html)