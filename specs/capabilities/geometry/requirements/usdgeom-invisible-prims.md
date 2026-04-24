# usdgeom-invisible-prims

| Code          | VG.034                              |
|---------------|-------------------------------------|
| Version       | 1.0.0                              |
| Validator     | {oav-validator-latest-link}`vg-034` |
| Compatibility | {compatibility}`Core USD`          |
| Tags          | {tag}`performance`                 |

## Summary

Avoid invisible prims when deactivation is more appropriate.

## Description

Prims with visibility set to "invisible" still consume memory and processing resources during stage traversal and composition. When prims are permanently invisible and not intended to be toggled visible at runtime, they should be deactivated instead. Deactivated prims are excluded from stage traversal and do not consume runtime resources.

## Why is it required?
- Reduces memory usage by excluding unnecessary prims from the stage
- Improves stage traversal performance
- Reduces file loading time
- Provides clearer intent - deactivation indicates the prim is not needed

## Examples

### Not recommended: Invisible prim consuming resources

```usd
#usda 1.0
(
    metersPerUnit = 1
    upAxis = "Z"
)

def Xform "World"
{
    def Mesh "HiddenCube"
    {
        token visibility = "invisible"
        float3[] extent = [(-0.5, -0.5, -0.5), (0.5, 0.5, 0.5)]
        int[] faceVertexCounts = [4, 4, 4, 4, 4, 4]
        int[] faceVertexIndices = [0, 1, 2, 3, 4, 5, 6, 7, 0, 1, 5, 4, 2, 3, 7, 6, 0, 3, 7, 4, 1, 2, 6, 5]
        point3f[] points = [(-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5), (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5)]
    }
}
```

### Recommended: Deactivated prim excluded from traversal

```usd
#usda 1.0
(
    metersPerUnit = 1
    upAxis = "Z"
)

def Xform "World"
{
    def Mesh "HiddenCube" (
        active = false
    )
    {
        float3[] extent = [(-0.5, -0.5, -0.5), (0.5, 0.5, 0.5)]
        int[] faceVertexCounts = [4, 4, 4, 4, 4, 4]
        int[] faceVertexIndices = [0, 1, 2, 3, 4, 5, 6, 7, 0, 1, 5, 4, 2, 3, 7, 6, 0, 3, 7, 4, 1, 2, 6, 5]
        point3f[] points = [(-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5), (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5)]
    }
}
```

## How to comply
- Use Scene Optimizer "Remove Prims" operation to deactivate invisible prims
- Only use visibility for prims that need runtime visibility toggling

## For More Information
- [UsdGeom Visibility Documentation](https://openusd.org/release/api/class_usd_geom_imageable.html#aab99049c7d2098c688464cf498009d9b)
- [USD Prim Active State](https://openusd.org/release/api/class_usd_prim.html#a538cd1e1a4b5c0f5f3b5e5d49c9c4d58)
- [Scene Optimizer Remove Prims](https://docs.omniverse.nvidia.com/extensions/latest/ext_scene-optimizer/operations.html#remove-prims)
