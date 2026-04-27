# usdgeom-mesh-primvar-usage

| Code          | VG.011                              |
|---------------|-------------------------------------|
| Version       | 1.0.0                              |
| Validator     | {oav-validator-latest-link}`vg-011` |
| Compatibility | {compatibility}`Core USD`          |
| Tags          | {tag}`performance`                 |

## Summary

Only include primvars that are actively used

## Description

Primvar data should be clean and purposeful. Only include primvars that are actively used by materials or other systems.

## Why is it required?

- Improves memory efficiency
- Improves file size
- Improves stage loading performance
- Provides cleaner, more maintainable geometry data

## Examples

### Invalid: Mesh with unused primvars

```usd
#usda 1.0

def Mesh "MeshWithUnusedPrimvars" {
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [(0,0,0), (1,0,0), (1,1,0), (0,1,0)]

    # Unused primvars
    float[] primvars:unused1 = [1.0, 1.0, 1.0, 1.0]
    color3f[] primvars:unused2 = [(1,0,0), (1,0,0), (1,0,0), (1,0,0)]
}
```

### Valid: Only used primvars

```usd
#usda 1.0

def Mesh "CleanMesh" {
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [(0,0,0), (1,0,0), (1,1,0), (0,1,0)]

    # UV coordinates used by material
    texCoord2f[] primvars:st = [(0,0), (1,0), (1,1), (0,1)]
}
```

## How to comply
- Remove unused primvars
- Clean up in source application
- Re-export with only necessary primvars

## For More Information
- [USD Primvar Documentation](https://openusd.org/release/api/class_usd_geom_primvar.html)