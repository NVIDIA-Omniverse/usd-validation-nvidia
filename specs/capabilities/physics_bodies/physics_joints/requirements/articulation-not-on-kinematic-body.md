# articulation-not-on-kinematic-body

| Code          | JT.ART.003                              |
|---------------|------------------------------------------|
| Version       | 1.0.0                                  |
| Validator     | {oav-validator-latest-link}`jt-art-003` |
| Compatibility | {compatibility}`PhysX`              |
| Tags          | {tag}`limitation`                   |

## Summary

In PhysX based simulators, like Omniverse Isaac Sim, Articulations are not allowed on kinematic bodies.

## Description

Articulations are only allowed on enabled non-kinematic rigid bodies.

## Why is it required?

* PhysX interprets the `UsdPhysicsArticulationRootAPI` as a marker for **dynamically simulated** reduced coordinate articulations, and kinematic bodies are not dynamically simulated.

## Examples

### Invalid: UsdPhysicsArticulationRootAPI applied to a kinematic body

```usd
#usda 1.0

def Cube "Cube" (
   prepend apiSchemas = ["PhysicsRigidBodyAPI", "PhysicsArticulationRootAPI"]
) {
   bool physics:kinematicEnabled = 1
}
```

### Valid: UsdPhysicsArticulationRootAPI applied to an enabled rigid body

```usd
#usda 1.0

def Cube "Cube" (
   prepend apiSchemas = ["PhysicsRigidBodyAPI", "PhysicsArticulationRootAPI"]
) {
}
```

## How to comply

Set the KinematicEnabled attribute of a RigidBodyAPI to False.

## For More Information

* [UsdPhysicsArticulationRootAPI Documentation](https://openusd.org/dev/api/class_usd_physics_articulation_root_a_p_i.html)
* [UsdPhysicsRigidBodyAPI Documentation](https://openusd.org/dev/api/class_usd_physics_rigid_body_a_p_i.html)
