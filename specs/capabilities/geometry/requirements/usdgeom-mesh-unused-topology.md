# usdgeom-mesh-unused-topology

| Code          | VG.018                              |
|---------------|-------------------------------------|
| Version       | 1.0.0                              |
| Validator     | {validator-latest-link}`scene-optimizer:vg-018` {oav-validator-latest-link}`vg-018` |
| Compatibility | {compatibility}`Core USD`          |
| Tags          | {tag}`performance`                 |

## Summary

Mesh topology should be without unused vertices, edges, or faces.

## Why is it required?
- Improves memory efficiency
- Improves file size
- Prevents potential rendering artifacts
- Provides clean, well-organized mesh data
- Avoids simulation issues

## Examples

### Invalid: Mesh with unused vertices

```usd
#usda 1.0

def Mesh "MeshWithUnusedPoints" {
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]  # Only uses first 4 vertices
    point3f[] points = [
        (0,0,0), (1,0,0), (1,1,0), (0,1,0),  # Used vertices
        (2,0,0), (3,0,0), (3,1,0), (2,1,0)   # Unused vertices
    ]
}
```

### Invalid: Mesh with unused vertices and primvars

Vertex and varying primvars have a value per vertex, so the values of the unused vertices are unused as well:

```usd
#usda 1.0

def Mesh "MeshWithUnusedPointsAndPrimvars"
{
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (2, 0, 0)]  # The last vertex is unused

    float[] primvars:value1 = [1, 2, 3, 4, 5] (interpolation = "vertex")
    float[] primvars:value2 = [1, 2, 3, 4, 5] (interpolation = "varying")
    float[] primvars:value3 = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] (interpolation = "vertex"; elementSize = 2)
    float[] primvars:value4 = [0, 1, 2, 3] (interpolation = "faceVarying")
    float3[] primvars:value5 = [(1, 0, 0), (2, 0, 0)] (interpolation = "vertex")
    int[] primvars:value5:indices = [0, 1, 0, 1, 1]
}
```

### Valid: Clean topology

```usd
#usda 1.0

def Mesh "CleanMesh" {
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [
        (0,0,0), (1,0,0), (1,1,0), (0,1,0)  # Only required vertices
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
- Remove unused vertices
- Clean up topology in source application
- Re-export with optimized topology

## For More Information
- [UsdGeom Mesh Documentation](https://openusd.org/release/api/class_usd_geom_mesh.html)