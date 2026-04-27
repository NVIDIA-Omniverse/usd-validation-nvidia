# usdgeom-unused-uvs

| Code          | VG.033                       |
|---------------|------------------------------|
| Version       | 1.0.0                        |
| Validator     | {validator-latest-link}`scene-optimizer:vg-033` |
| Compatibility | {compatibility}`Core USD`    |
| Tags          | {tag}`performance`           |

## Summary

Do not author unused texture coordinates.

## Description

Authoring unused UVs/texture coordinates can cause unnecessary GPU and system memory usage and larger file sizes. As the data takes up space on a mesh, it is best to avoid having to store and process it unless it is actually required by a material.

## Why is it required?
- Reducing GPU memory usage
- Reducing system memory usage
- Reducing file size

## How to comply
- Do not author texture coordinates if they are not used
- Use Scene Optimizer "Remove Unused UVs" operation to clean up

## For More Information
- [Scene Optimizer Remove Unused UVs](https://docs.omniverse.nvidia.com/extensions/latest/ext_scene-optimizer/operations.html#remove-unused-uvs)
