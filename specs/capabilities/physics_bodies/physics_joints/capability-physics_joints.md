# Physics Joints

## Overview

This capability provides requirements for creating connections between rigid bodies in physics simulations. Joints constrain the relative motion between bodies, enabling complex mechanical systems and articulated structures.

- Joints are fixed attachments that can represent the way a drawer is attached to a cabinet, a wheel to a car, or links of a robot to each other. A joint constrains the
movement of rigid bodies and can be created between two rigid bodies or between one rigid body and world.
- Mathematically, jointed assemblies can be modeled either in maximal (world space) or reduced (relative to other bodies) coordinates. An extension to the joint system based on reduced coordinates is provided with **Articulations**.

This capability is often paired with the Rigid Bodies capability to create comprehensive physics simulations.

## Summary

- A **UsdPhysicsJoint prim** or one of its subtypes can be used to constrain two rigid bodies together, or to constrain a single rigid body to the World. This is achieved by setting the joint's Body0 and Body1 relationship targets to either two rigid bodies or one to a rigid body and leaving the other one empty.
- Any prim of the USD scene graph hierarchy may be marked with an **UsdPhysicsArticulationRootAPI**. This informs the simulation that any joints found in the subtree should preferentially be simulated using a reduced coordinate approach.

## Schema / OpenUSD Specification
Joints are created using the following schemas that are part of the core OpenUSD specification.

- [Joints](https://openusd.org/dev/api/usd_physics_page_front.html#usdPhysics_joints)
- [Joint Subtypes](https://openusd.org/dev/api/usd_physics_page_front.html#usdPhysics_joint_subtypes)

## Requirements

<!-- PHYSICS_JOINTS_REQUIREMENTS_LIST_START -->

```{requirements-table}
```

<!-- PHYSICS_JOINTS_REQUIREMENTS_LIST_END -->
