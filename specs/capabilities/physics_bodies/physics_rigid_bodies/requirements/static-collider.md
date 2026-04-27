# static-collider

| Code          | RB.COL.002                    |
|---------------|-------------------------------|
| Version       | 1.0.0                        |
| Validator     |                               |
| Compatibility | {compatibility}`OpenUSD`     |
| Tags          | {tag}`correctness`           |

## Summary

If an asset is expected to be static (no movement happens), it can not contain a rigid body, only a Collider body.

## Description

The UsdPhysicsCollisionAPI defines collisions only. The collisions will be considered "static collisions" (without movement), if the **UsdPhysicsRigidBodyAPI** is **not** present.

## Why is it required?

* If an asset should act as a collider, but it is not expected to move during simulation, it **cannot** have UsdPhysicsRigidBodyAPI applied.

## Examples

### Invalid: Collision that should be static but includes a rigid body API

```usd
#usda 1.0

def Cube "cube" (
   prepend apiSchemas = ["PhysicsRigidBodyAPI", "PhysicsCollisionAPI"]
) {
}
```

### Valid: Static collision

```usd
#usda 1.0

def Cube "cube" (
   prepend apiSchemas = ["PhysicsCollisionAPI"]
) {
}
```

## How to comply

The **UsdPhysicsCollisionAPI** schema has to be applied to a UsdGeomGPrim, but that prim or any of its parent prims cannot also have the **UsdPhysicsRigidBodyAPI** applied.

## For More Information

* [UsdPhysics Collision Documentation](https://openusd.org/dev/api/usd_physics_page_front.html#usdPhysics_collision_shapes)
* [UsdPhysicsCollisionAPI Documentation](https://openusd.org/dev/api/class_usd_physics_collision_a_p_i.html)
* [UsdPhysicsRigidBodyAPI Documentation](https://openusd.org/dev/api/class_usd_physics_rigid_body_a_p_i.html)
