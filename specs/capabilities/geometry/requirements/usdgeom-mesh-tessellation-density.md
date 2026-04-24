# usdgeom-mesh-tessellation-density

| Code          | VG.013                    |
|---------------|---------------------------|
| Version       | 1.0.0                    |
| Validator     |                           |
| Compatibility | {compatibility}`Core USD` |
| Tags          | {tag}`performance`       |

## Summary

Use appropriate tessellation density for geometry

## Description

Meshes should use appropriate tessellation density for their visual requirements. The tessellation density should balance visual fidelity with performance and memory usage.

For a faster but less thorough check, use the Mesh Vertex Count validator, which considers only vertex count rather than the overall shape when assessing excessive mesh density.

## Why is it required?
- Improves memory efficiency
- Improves rendering performance
- Improves file size
- Balances visual quality with performance (e.g. for VR, Physics etc)
- Maintains workable/reasonable complexity

## Examples

```usd
# Not recommended: Excessive tessellation for a simple shape
def Mesh "OverTessellatedPlane" {
    int[] faceVertexCounts = [4, 4, 4, 4, 4, 4, 4, 4, 4, 4]  # 10 quads for flat surface
    int[] faceVertexIndices = [...]  # Many vertices for a simple shape
    point3f[] points = [...]
}

# Recommended: Efficient tessellation
def Mesh "OptimizedPlane" {
    int[] faceVertexCounts = [4]  # Single quad for flat surface
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [(0,0,0), (1,0,0), (1,1,0), (0,1,0)]
}
```

## How to comply
- Re-tessellate with adjusted maximum mean error settings
- Use decimation tools to reduce polygon count with maximum mean error setting
- Convert to USD with optimized tessellation parameters
- Scene Optimizer - Decimate Mesh
- Scene Optimizer - Remesh Meshes

## For More Information
- [UsdGeom Mesh Documentation](https://openusd.org/release/api/class_usd_geom_mesh.html)
- [Scene Optimizer Decimate Meshes](https://docs.omniverse.nvidia.com/extensions/latest/ext_scene-optimizer/operations.html#decimate-meshes)
