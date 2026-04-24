# usdgeom-mesh-lamina-faces

| Code          | VG.032                              |
|---------------|-------------------------------------|
| Version       | 1.0.0                              |
| Validator     | {validator-latest-link}`scene-optimizer:vg-032` |
| Compatibility | {compatibility}`Core USD`          |
| Tags          | {tag}`performance`                 |

## Summary

Faces should not be lamina.

## Description

Lamina faces are those that share all the same vertices. This means there are two or more identical overlapping faces. This is wasteful, and can also cause rendering artifacts if the faces have different materials. They can be created in a variety of ways. For example: accidentally duplicating faces on a mesh, merging objects with coincident faces and then merging vertices, or modeling operations like booleans on meshes that have coincident faces.

## Why is it required?

- Improves memory efficiency
- Prevents rendering artifacts
- Avoids physics simulation issues

## Examples

### Invalid: Lamina faces

```usd
#usda 1.0

def Mesh "planeWithLaminaFaces" ()
{
    int[] faceVertexCounts = [4, 4]
    int[] faceVertexIndices = [0, 1, 3, 2, 0, 1, 3, 2]
    point3f[] points = [(-1, 0, 1), (1, 0, 1), (-1, 0, -1), (1, 0, -1)]
}
```

### Valid: No lamina faces

```usd
#usda 1.0

def Mesh "planeWithNoLaminaFaces" ()
{
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 3, 2]
    point3f[] points = [(-1, 0, 1), (1, 0, 1), (-1, 0, -1), (1, 0, -1)]
}
```

## How to comply
- Clean up meshes using Scene Optimizer
- Remove lamina faces
- Fix mesh generation settings

## For More Information
- [UsdGeom Mesh Documentation](https://openusd.org/release/api/class_usd_geom_mesh.html)
- [Scene Optimizer Mesh Cleanup](https://docs.omniverse.nvidia.com/extensions/latest/ext_scene-optimizer/operations.html#mesh-cleanup)
