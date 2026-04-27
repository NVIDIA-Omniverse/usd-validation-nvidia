# usdgeom-mesh-internal-geometry

| Code          | VG.003                              |
|---------------|-------------------------------------|
| Version       | 1.0.0                              |
| Validator     | {validator-latest-link}`scene-optimizer:vg-003` |
| Compatibility | {compatibility}`OpenUSD`          |
| Tags          | {tag}`performance`                 |

## Parameters

| Parameter          | Type | Default Value |
|--------------------|------|---------------|
| USE_GPU            | bool | False         |
| CHECK_TRANSPARENCY | bool | False         |

## Summary

Only include geometry that contributes to visualization or simulation

## Description

Assets should only include geometry that contributes to the final render. Geometry that is completely enclosed within other geometry and never visible should be excluded to optimize performance and memory usage.

## Why is it required?
- Improves memory efficiency
- Optimizes raytracing performance
- Improves file size
- Avoids simulation issues

## How to comply
- Remove completely enclosed internal geometry
- Use visibility attributes for geometry that may be exposed
- Run Scene Optimizer - Find Hidden Meshes tool

## For More Information
- [UsdGeom Visibility Documentation](https://openusd.org/release/api/class_usd_geom_imageable.html)