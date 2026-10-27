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

### Invalid: Normals do not match the points

```usd
#usda 1.0

def Mesh "MeshWithIncompleteNormals"
{
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 0, 0)]  # Co-located with the first point
    # Vertex interpolation requires one normal per point
    normal3f[] normals = [(0, 0, 1), (0, 0, 1), (0, 0, 1), (0, 0, 1)] (
        interpolation = "vertex"
    )
}
```

### Invalid: Primvar does not match the points

```usd
#usda 1.0

def Mesh "MeshWithIncompletePrimvar"
{
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 0, 0)]  # Co-located with the first point
    # Vertex interpolation requires one value per point
    texCoord2f[] primvars:st = [(0, 0), (1, 0), (1, 1), (0, 1)] (
        interpolation = "vertex"
    )
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

### Valid: Mesh without data

```usd
#usda 1.0

def Mesh "EmptyMesh"
{
}
```

## How to comply
- Weld co-located vertices in Source Application
- Fix mesh generation settings
- Scene Optimizer - Merge Vertices

## For More Information
- [UsdGeom Mesh Documentation](https://openusd.org/release/api/class_usd_geom_mesh.html)