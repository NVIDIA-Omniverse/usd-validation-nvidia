# rigid-body-no-nesting

| Code          | RB.006                              |
|---------------|-------------------------------------|
| Version       | 1.0.0                               |
| Validator     | {oav-validator-latest-link}`rb-006` |
| Compatibility | {compatibility}`PhysX`              |
| Tags          | {tag}`limitation`                   |


## Summary

In PhysX based simulators, like Omniverse Isaac Sim, Rigid bodies can not be nested unless xformOp reset xform stack is used.

## Description

Since maximal coordinate simulation computes the world transformation, **it has to be applied to the local transformation stack of the UsdGeomXformable**. If rigid bodies are nested, it requires extra computation to make the transformation parent-relative. To avoid this complication, **if rigid bodies are nested, they must have their xformOp stack reset set.**

## Why is it required?

- Assets with `UsdPhysicsRigidBodyAPI` define rigid bodies for the simulator. Prims with this API will have their xformOp attributes updated after each simulation step, and as the PhysX simulator natively computes world transformations, it is most efficient for write-back to USD to store the same data directly on the Prims.

## Examples

### Invalid: Nested rigid bodies

```usd
#usda 1.0

def Xform "Xform" (
   prepend apiSchemas = ["PhysicsRigidBodyAPI"]
)
{
   def Cube "cube" (
      prepend apiSchemas = ["PhysicsRigidBodyAPI", "PhysicsCollisionAPI"]
   ) {
   }
}
```

### Valid: Rigid bodies nested but with xformOp stack reset

```usd
#usda 1.0

def Xform "Xform" (
   prepend apiSchemas = ["PhysicsRigidBodyAPI"]
)
{
   def Cube "cube" (
      prepend apiSchemas = ["PhysicsRigidBodyAPI", "PhysicsCollisionAPI"]
   ) {
      quatd xformOp:orient = (1, 0, 0, 0)
      double3 xformOp:scale = (1, 1, 1)
      double3 xformOp:translate = (0, 0, 0)
      uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient", "xformOp:scale"]
   }
}
```

## How to comply

The UsdPhysicsRigidBodyAPI cannot be nested unless xformOp resetXformStack is used.
