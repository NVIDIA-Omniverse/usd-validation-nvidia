# usdgeom-mesh-vertex-count

| Code          | VG.021                    |
|---------------|---------------------------|
| Version       | 1.0.0                    |
| Validator     | {validator-latest-link}`scene-optimizer:vg-021` |
| Compatibility | {compatibility}`Core USD` |
| Tags          | {tag}`performance`       |

## Summary

Use appropriate vertex count for geometry

## Description

Meshes should use appropriate vertex counts for their visual requirements. The vertex count should balance visual fidelity with performance and memory usage. This is a quick check for high density meshes.

For a more thorough but slower check, use the Mesh Tessellation Density validator, which considers shape rather than just total vertex count when assessing excessive mesh density.

## Why is it required?
- High memory usage
- Slower rendering performance
- Increased file size

## Examples

```usd
# Not recommended: High vertex count
def Mesh "OverlyFacedPlane" {
    int[] faceVertexCounts = [4, 4, 4, 4, 4, ...]  # many quads
    int[] faceVertexIndices = [...]  # Many vertices
    point3f[] points = [...]
}

# Recommended: Reduced vertex count
def Mesh "OptimizedPlane" {
    int[] faceVertexCounts = [4,4,4,4]  # Fewer quads
    int[] faceVertexIndices = [...]
    point3f[] points = [...]
}
```

## How to comply
- Re-tessellate with adjusted vertex count settings
- Use decimation tools to reduce vertex count
- Convert to USD with optimized tessellation parameters
- Scene Optimizer - Decimate Mesh
- Scene Optimizer - Remesh Meshes

## For More Information
- [UsdGeom Mesh Documentation](https://openusd.org/release/api/class_usd_geom_mesh.html)
- [Scene Optimizer Decimate Meshes](https://docs.omniverse.nvidia.com/extensions/latest/ext_scene-optimizer/operations.html#decimate-meshes)
- [Scene Optimizer Remesh Meshes](https://docs.omniverse.nvidia.com/extensions/latest/ext_scene-optimizer/operations.html#remesh-meshes)
