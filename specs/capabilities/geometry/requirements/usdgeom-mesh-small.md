# usdgeom-mesh-small

| Code          | VG.012                    |
|---------------|---------------------------|
| Version       | 1.0.0                    |
| Validator     |                           |
| Compatibility | {compatibility}`Core USD` |
| Tags          | {tag}`performance`       |

## Parameters

| Parameter      | Type  | Default Value |
|----------------|-------|---------------|
| SIZE_THRESHOLD | float | 0.001        |

## Summary

Remove meshes from the scene that are below the extent size threshold.

## Description

Optimize scene performance and reduce mesh count by removing meshes that have an extent size smaller than the threshold.

The `SIZE_THRESHOLD` parameter defines the minimum size a mesh's largest extent dimension can be. Any mesh with an
extent size less than this should be removed from the scene.

## Why is it required?
- Reduces memory overhead
- Optimizes rendering performance, specifically on GPU (TLAS size is reduced)
- Enables better batch processing and culling

## Examples

```usd
# Not recommended: Many tiny separate meshes
def Xform "TinyMeshes" {
    def Mesh "SmallCube_1" {
        float3[] extent = [(-0.0001, -0.0001, -0.0001), (0.0001, 0.0001, 0.0001)]
        int[] faceVertexCounts = [4, 4, 4, 4, 4, 4]
        int[] faceVertexIndices = [0, 1, 2, 3, ...]
        point3f[] points = [(-0.0001, -0.0001, -0.0001), ...]
    }
    
    def Mesh "SmallCube_2" {
        float3[] extent = [(-0.0001, -0.0001, 0.0002), (0.0001, 0.0001, 0.004)]
        int[] faceVertexCounts = [4, 4, 4, 4, 4, 4]
        int[] faceVertexIndices = [0, 1, 2, 3, ...]
        point3f[] points = [(-0.0001, -0.0001, 0.0002), ...]
    }
}

# Recommended: Remove these meshes from the stage.
```

## How to comply
- Remove small meshes using the Scene Optimizer Remove Small Meshes or Remove Degenerate meshes operations
- Review mesh generation settings

## For More Information
- [UsdGeom Mesh Documentation](https://openusd.org/release/api/class_usd_geom_mesh.html)
- [Scene Optimizer](https://docs.omniverse.nvidia.com/extensions/latest/ext_scene-optimizer/operations.html)