# intentional-origin-positioning

| Code          | HI.010                                          |
|---------------|-------------------------------------------------|
| Version       | 1.0.0                                           |
| Validator     | {manual-validation}`manual-validation-required` |
| Compatibility | {compatibility}`Core USD`                       |
| Tags          | {tag}`essential`                               |

## Summary

Origins of prims representing objects or groups that require placement should be positioned intentionally

## Description

Prims and meshes that require placement, positioning or rotation shall be located at intuitive and logical positions, such as the center of the object's base (bottom surface) or the center of the object's rotation axis.

## Why is it required?

Intentionally placed origins provide several benefits:
- They enable intuitive placement and transformation behavior, for example with "snap to grid" functionality
- They create relevant local space coordinates with real-world meaning
- They establish reliable "contracts" between asset producers and consumers
- Provide consistent behavior for different assets

These benefits are particularly important for consumers who may be authoring placement or transform opinions, or using transformation data from simulation or time series sources.

## Examples

### Valid: Cube shaped mesh sitting on the ground plane

```usd
#usda 1.0
(
    metersPerUnit = 1.0
    upAxis = "Z"
)

def Xform "World"
{
    def Mesh "Cube"
    {
        point3f[] points = [ ( -0.5, -0.5, 0.0 ), ( 0.5, -0.5, 0.0 ), ( 0.5, 0.5, 0.0 ), ( -0.5, 0.5, 0.0 ), ( -0.5, -0.5, 1.0 ), ( 0.5, -0.5, 1.0 ), ( 0.5, 0.5, 1.0 ), ( -0.5, 0.5, 1.0 ) ]  # 0…7: bottom back-left, bottom back-right, bottom front-right, bottom front-left, top back-left, top back-right, top front-right, top front-left

        int[] faceVertexCounts = [ 4, 4, 4, 4, 4, 4 ]  # six quads

        int[] faceVertexIndices = [ 0,1,2,3, 4,7,6,5, 0,4,5,1, 1,5,6,2, 2,6,7,3, 3,7,4,0 ]  # bottom, top, back, right, front, left faces

        uniform token subdivisionScheme = "none"

        point3f[] extent = [ ( -0.5, -0.5, 0.0 ), ( 0.5, 0.5, 1.0 ) ]  # min and max corners
    }
}
```

### Valid: Ceiling fan with origin at the top of the down rod

```usd
#usda 1.0
(
    metersPerUnit = 1.0
    upAxis = "Z"
)

def Xform "CeilingFan" ()
{
    def Cylinder "DownRod" {
        float3 xformOp:translate = (0, -0.5  , 0)  # Blade extends from center
        float3 xformOp:scale = (0.1, 0.5, 0.1)
        token axis = "Y"
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
    }

    def Cube "FanBlade" {
        float3 xformOp:translate = (1, -1, 0)  # Blade extends from center
        float3 xformOp:scale = (1, 0.02, 0.1)
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
    }
}
```

### Valid: Door panel with origin at the hinge point

```usd
#usda 1.0
(
    metersPerUnit = 1.0
    upAxis = "Z"
)

def Xform "World"
{
    def Mesh "DoorPanel"
    {
        point3f[] points = [ (0, 0, 0), (1, 0, 0), (1, 0.05, 0), (0, 0.05, 0), (0, 0, 1), (1, 0, 1), (1, 0.05, 1), (0, 0.05, 1) ]  # 0…7: bottom-left-hinge, bottom-right-hinge, bottom-right-thickness, bottom-left-thickness, top-left-hinge, top-right-hinge, top-right-thickness, top-left-thickness

        int[] faceVertexCounts = [ 4, 4, 4, 4, 4, 4 ]  # six quads

        int[] faceVertexIndices = [
            0,1,2,3,    # bottom face
            4,7,6,5,    # top face
            3,2,6,7,    # front face (outer)
            0,4,5,1,    # hinge face (at X=0,Y=0)
            1,5,6,2,    # right face
            3,7,4,0     # left face
        ]

        uniform token subdivisionScheme = "none"
        point3f[] extent = [ (0, 0, 0), (1, 0.05, 1) ]  # min and max corners
    }
}
```

## How to comply

Position geometry so that their origin is placed at a intentional location, such as the center of the object's base (bottom surface) or the center of the object's rotation axis.

## For more information

- [UsdGeomXformCommonAPI Documentation](https://openusd.org/release/api/class_usd_geom_xform_common_a_p_i.html)
- [USD Transform Operations](https://openusd.org/release/api/class_usd_geom_xformable.html)
- [USD Transformations Tutorial](https://openusd.org/dev/tut_xforms.html)