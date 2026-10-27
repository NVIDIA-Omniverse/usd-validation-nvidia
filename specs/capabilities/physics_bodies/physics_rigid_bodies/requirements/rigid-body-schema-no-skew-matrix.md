# rigid-body-schema-no-skew-matrix

| Code          | RB.009                              |
|---------------|-------------------------------------|
| Version       | 1.0.0                              |
| Validator     | {oav-validator-latest-link}`rb-009` |
| Compatibility | {compatibility}`OpenUSD`           |
| Tags          | {tag}`correctness`                 |

## Summary

Rigid bodies have to be UsdGeomXformable prims without skew matrix.

## Description

Simulation does not support scale, hence UsdPhysicsRigidBodyAPI has to be applied to any UsdGeomXformable prim that does not contain a skew  in the world transformation matrix.

## Why is it required?

- Assets with UsdPhysicsRigidBodyAPI define a rigid body for the simulator and need to make sure that non physical scale like skew is **not** applied.

## Examples

### Valid: Rigid body without a skew matrix

```usd
#usda 1.0

def Xform "RigidBody" (
    prepend apiSchemas = ["PhysicsRigidBodyAPI"]
)
{
    double3 xformOp:translate = (0, 1, 0)
    float3 xformOp:rotateXYZ = (0, 45, 0)
    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
}
```

### Valid: Rigid body with a non-uniform scale and no skew

```usd
#usda 1.0

def Xform "RigidBody" (
    prepend apiSchemas = ["PhysicsRigidBodyAPI"]
)
{
    float3 xformOp:scale = (1, 2, 3)
    uniform token[] xformOpOrder = ["xformOp:scale"]
}
```

### Invalid: Rigid body with a skew matrix

```usd
#usda 1.0

def Xform "RigidBody" (
    prepend apiSchemas = ["PhysicsRigidBodyAPI"]
)
{
    # The Y axis is sheared along X
    matrix4d xformOp:transform = ( (1, 0, 0, 0), (1, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1) )
    uniform token[] xformOpOrder = ["xformOp:transform"]
}
```

## How to comply

UsdPhysicsRigidBodyAPI has to be applied to a UsdGeomXformable that does not contain a skew  (orientation scale) in the world transform matrix.

## For More Information

- [UsdPhysics Rigid Body Documentation](https://openusd.org/dev/api/usd_physics_page_front.html#usdPhysics_rigid_bodies)
- [UsdPhysicsRigidBodyAPI Documentation](https://openusd.org/dev/api/class_usd_physics_rigid_body_a_p_i.html)
- [UsdGeomXformable Documentation](https://openusd.org/dev/api/class_usd_geom_xformable.html)
