# usdgeom-mesh-count

| Code          | VG.RTX.002                              |
|---------------|-----------------------------------------|
| Version       | 1.0.0                                   |
| Validator     | {oav-validator-latest-link}`vg-rtx-002` |
| Compatibility | {compatibility}`RTX`                    |
| Tags          | {tag}`performance`                      |

## Summary

Use appropriate mesh count for scene.

## Description

Mesh count must not exceed RTX limit.

RTX has a limit on the number of acceleration structures supported. This number is OS-dependent and is slightly
lower on Linux (Vulkan) than Windows. It is approximately 300k structures. The number of meshes does not exactly
map onto the number of acceleration structures, but is likely to be close. Therefore a number of meshes approaching
300k or so is likely to be a problem for RTX. Any meshes that are loaded beyond this limit will not be displayed.

## Why is it required?

- Viewing all objects in scene

## How to comply

- Merge meshes in source data
- Merge meshes using available Scene Optimizer operations

## For More Information

- [UsdGeom Mesh Documentation](https://openusd.org/release/api/class_usd_geom_mesh.html)
- [Scene Optimizer Merge Static Meshes](https://docs.omniverse.nvidia.com/extensions/latest/ext_scene-optimizer/operations.html#merge-static-meshes)
