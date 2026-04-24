# Rigid Body Mass

| Code          | RB.007                    |
|---------------|---------------------------|
| Version       | 1.0.0                    |
| Validator     | {oav-validator-latest-link}`rb-007` |
| Compatibility | {compatibility}`OpenUSD` |
| Tags          | {tag}`high-quality`      |

## Summary

Rigid bodies _or_ their descendent collision shapes should have a mass & their other inertial properties explicitly specified.

## Description

Rigid bodies _or_ their descendent collision shapes must have a mass specification using the `UsdPhysicsMassAPI`.

- `physics:mass`: Specifies the mass of the object directly

Alternatively, if its more convenient, density can be specified instead of mass:

- `physics:density`: Specifies the mass density of the object in kg/m³. When specified, mass is computed as density × volume.

Note: Density can be specified either through the `MassAPI` or through the [MaterialAPI](https://openusd.org/dev/api/class_usd_physics_material_a_p_i.html). When both specify density, the `MassAPI` density takes precedence. Additionally, if `MassAPI` specifies a mass value, it takes precedence over any density values.

Inertia should also be specified for any enabled rigid body or collider that can move dynamically (has degrees of freedom):

- `physics:centerOfMass`: Defines the center of mass in the prim's local space (in meters).
- `physics:diagonalInertia`: Specifies the diagonalized inertia tensor along principal axes (in kg⋅m²).
- `physics:principalAxes`: Defines the orientation of the inertia tensor's principal axes in the prim's local space.

All units must be consistent with the stage's unit system as defined by [meters-per-unit](/capabilities/core/units/requirements/meters-per-unit) and [kilograms-per-unit](/capabilities/core/units/requirements/kilograms-per-unit).

## Why is it required?

- If mass & inertia is not specified, simulators will compute these values automatically. This is often inaccurate as objects are modelled without internal details. Specifying mass & inertia allows for more accurate simulation.

## Examples

### Invalid: No mass or inertia specified

```usd
#usda 1.0

def Xform "RobotHead" () {
   prepend apiSchemas = ["PhysicsRigidBodyAPI"]

   def Mesh "Head" (
      prepend apiSchemas = ["PhysicsCollisionAPI"]
   )
   {
   }
}
```

### Invalid: Illegal mass and inertia values

```usd
#usda 1.0

def Xform "RobotHead" () {
   prepend apiSchemas = ["PhysicsRigidBodyAPI"]

   def Mesh "Head" (
      prepend apiSchemas = ["PhysicsCollisionAPI", "PhysicsMassAPI"]
   )
   {
         float physics:mass = -0.1  # mass cannot be negative
         # centerOfMass is missing
         quatf physics:principalAxes = (0.5, 0.5, 0.5, 0.5)  # not a unit quaternion
         float3 physics:diagonalInertia = (-0.01, -0.02, -0.03)  # moment of inertia cannot be negative
   }
}
```

### Valid: Mass & inertia fully specified

```usd
#usda 1.0

def Xform "RobotHead" () {
   prepend apiSchemas = ["PhysicsRigidBodyAPI"]

   def Cube "Jaw" (
      prepend apiSchemas = ["PhysicsCollisionAPI", "PhysicsMassAPI"]
   )
   {
         float physics:mass = 2.93554
         point3f physics:centerOfMass = (0.00318289, -0.0743222, 0.00881461)
         quatf physics:principalAxes = (0.502599, 0.584437, -0.465998, 0.434366)
         float3 physics:diagonalInertia = (0.0629567, 0.0411924, 0.0246371)
   }
}
```

### Valid: Mass specified on Rigid Body

```usd
#usda 1.0

def Xform "RobotBody" () {
   prepend apiSchemas = ["PhysicsRigidBodyAPI", "PhysicsMassAPI"]

   float physics:mass = 2.32712
   point3f physics:centerOfMass = (-0.00160396, 0.0292536, -0.0972966)
   quatf physics:principalAxes = (0.919031, 0.125604, 0.0751531, -0.366003)
   float3 physics:diagonalInertia = (0.0579335, 0.0449144, 0.0130634)

   def Mesh "Body" (
      prepend apiSchemas = ["PhysicsCollisionAPI"]
   )
   {
   }

   def Cube "Leg" (
      prepend apiSchemas = ["PhysicsCollisionAPI"]
   )
   {
   }
}
```

## How to comply

- Apply the `UsdPhysicsMassAPI` to the rigid body or collider & author the `physics:mass`, `physics:centerOfMass`, `physics:diagonalInertia`, and `physics:principalAxes` attributes with values which are as accurate as possible.

- Note the precedence rules for mass and density:
  - MassAPI mass value takes precedence over any density values
  - MassAPI density takes precedence over MaterialAPI density
  - If no mass or density is specified, simulators will compute mass automatically
- Center of mass should be specified in the prim's local space
- Inertia tensor should be diagonalized and aligned with principal axes
- All units must be consistent with the stage's unit system:
  - Linear measurements (centerOfMass) should use the stage's metersPerUnit
  - Mass measurements (mass, density) should use the stage's kilogramsPerUnit
  - Inertia measurements should use the appropriate combination of mass and length units

## Related Requirements

- [meters-per-unit](/capabilities/core/units/requirements/meters-per-unit)
- [kilograms-per-unit](/capabilities/core/units/requirements/kilograms-per-unit)

## For More Information

- [UsdPhysicsMassAPI Documentation](https://openusd.org/dev/api/class_usd_physics_mass_a_p_i.html)
- [UsdPhysicsRigidBodyAPI Documentation](https://openusd.org/dev/api/class_usd_physics_rigid_body_a_p_i.html)
- [UsdPhysicsMaterialAPI Documentation](https://openusd.org/dev/api/class_usd_physics_material_a_p_i.html)
