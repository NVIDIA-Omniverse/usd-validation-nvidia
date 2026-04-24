# mesh-xform-positioning

| Code          | VG.023                              |
|---------------|-------------------------------------|
| Version       | 1.0.0                               |
| Validator     | {manual-validation}`manual-validation-required` |
| Compatibility | {compatibility}`Core USD`           |
| Tags          | {tag}`correctness`                  |

## Summary

Meshes should be positioned using xform ops, not by embedding positions into point positions.

## Description

Mesh positioning should be applied through USD's transformation stack (xform ops) rather than being "baked" into the point positions. This makes mesh positioning clearly addressable in opinions and overs, enables reuse of the same mesh in different places and enables memory de-duplication for re-occuring meshes.

## Why is it required?

- Ensures that transformation gizmos in USD viewers work as expected
- Allows for descriptive transformation manipulation by consumers / users - "position the mesh at a height of 1m"
- Maintains separation between geometry and transformation data
- Keeps CPU and GPU memory usage down by not having to store the same mesh data multiple times (see [identical-mesh-consistency](identical-mesh-consistency.md))


```{note}
In OpenUSD, gPrims (such as Meshes, Curves, Xforms, etc.) are all transformable. It is not required to use an explicit `Xform` "parent" prim to apply transformations to geometry such as meshes.

In some cases / workflows there might be a conventional choice to use an explicit Xform prim to apply transformations to a mesh. This is not a technical requirement and may lead to performance overheads in very large scenes (see "Leverage transformable gprims" [here](https://openusd.org/release/maxperf.html)).
```


```usd
#usda 1.0

def Xform "MyObject" (
) {
    # Recommended: Mesh positioned using xform ops
    def Mesh "Geometry" {
        float3 xformOp:translate = (5, 0, 0)
        float3 xformOp:rotateXYZ = (0, 45, 0)
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]

        point3f[] points = [(-1, 0, -1), (1, 0, -1), (1, 0, 1), (-1, 0, 1)]
        # Mesh points are in local space, transformations applied via xform ops
    }

    # Not Recommended: Transformation baked into mesh points
    def Mesh "BadGeometry" {
        point3f[] points = [(2.54, 0, -2.54), (7.54, 0, -2.54), (7.54, 0, 2.54), (2.54, 0, 2.54)]
        # Mesh points have transformation baked in, making reuse difficult
    }
}
```

## How to comply

- Keep mesh points in local coordinate space
- Apply transformations using xform ops on xformable prims (xforms, meshes, etc.)
- Avoid pre-transforming mesh vertices during asset creation

## For more information

- [USD Transform Operations](https://openusd.org/release/api/class_usd_geom_xformable.html)
- [UsdGeomMesh Documentation](https://openusd.org/release/api/class_usd_geom_mesh.html)
- [Maximizing USD Performance](https://openusd.org/release/maxperf.html)