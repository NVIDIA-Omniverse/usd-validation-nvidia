# usdgeom-mesh-manifold

| Code          | VG.007                              |
|---------------|-------------------------------------|
| Version       | 1.0.0                              |
| Validator     | {validator-latest-link}`scene-optimizer:vg-007` {oav-validator-latest-link}`vg-007` |
| Compatibility | {compatibility}`Core USD`          |
| Tags          | {tag}`correctness`                 |

## Summary

Mesh geometry must be manifold

## Description

Mesh geometry must maintain manifold topology to ensure proper simulation and rendering behavior. Non-manifold issues include:

- Non-manifold vertices: Two or more faces share a single vertex but are not connected to each other via an edge or via one or more intermediate faces. Examples are two planes or two cubes touching at one shared corner vertex.
- Non-manifold edges: Three or more faces share an edge
- Inconsistent winding: Adjacent faces have opposite vertex winding order

## Why is it required?
- Prevents visual artifacts
- Avoids potential simulation issues

## Examples

### Invalid: Non-manifold edge due to inconsistent winding

```usd
#usda 1.0

def Mesh "BadMesh" {
    int[] faceVertexCounts = [4, 4]
    int[] faceVertexIndices = [0, 1, 2, 3, 3, 2, 4, 5]  # Edge 2-3 used twice
    point3f[] points = [(0,0,0), (1,0,0), (1,1,0), (0,1,0), (1,2,0), (0,2,0)]
}
```

### Valid: Manifold mesh
```usd
#usda 1.0

def Mesh "GoodMesh" {
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [(0,0,0), (1,0,0), (1,1,0), (0,1,0)]
}
```

## How to comply
- Use mesh repair tools to weld edges and vertices
- Align face normals
- Reconvert to USD after repair


## For More Information
- [UsdGeom Mesh Documentation](https://openusd.org/release/api/class_usd_geom_mesh.html)
- [Scene Optimizer Mesh Cleanup - Make Manifold option](https://docs.omniverse.nvidia.com/extensions/latest/ext_scene-optimizer/operations.html#mesh-cleanup)
