# usdgeom-particle-field-gaussian-splat

| Code          | VG.035                              |
|---------------|-------------------------------------|
| Version       | 1.0.0                               |
| Validator     | {oav-validator-latest-link}`vg-035` |
| Compatibility | {compatibility}`Core USD`           |
| Tags          | {tag}`correctness`                  |

## Summary

`ParticleField3DGaussianSplat` prims must satisfy schema and data consistency rules required for interoperable 3D Gaussian splat assets. General stage metadata (for example default prim, meters per unit, and up axis) is validated by other requirements in the geometry and layout capabilities.

## Description

This requirement applies to OpenUSD **26.03** and later, where `UsdVol.ParticleField3DGaussianSplat` is available. Each splat prim must author all required attributes with consistent array lengths, valid value ranges, and spherical harmonics configuration that matches the declared SH degree.

## Why is it required?

- Ensures splat data can be consumed reliably by renderers and tools that implement the schema
- Catches common export mistakes (missing attributes, length mismatches, invalid quaternions) before delivery
- Aligns runtime validation with the published `ParticleField3DGaussianSplat` layout

## Examples

### Valid: Minimal conforming splat with stage metadata

```usd
#usda 1.0
(
    defaultPrim = "Splat"
    metersPerUnit = 1
    upAxis = "Y"
)

def ParticleField3DGaussianSplat "Splat"
{
    point3f[] positions = [(0,0,0), (1,0,0)]
    float3[] scales = [(1,1,1), (1,1,1)]
    quatf[] orientations = [(1,0,0,0), (1,0,0,0)]
    float[] opacities = [0.5, 0.5]
    int radiance:sphericalHarmonicsDegree = 0
    float3[] radiance:sphericalHarmonicsCoefficients = [(0,0,0), (0,0,0)] (
        interpolation = "vertex"
        elementSize = 1
    )
    float3[] extent = [(-0.5,-0.5,-0.5), (1.5,0.5,0.5)]
}
```

### Invalid: Opacity outside [0, 1]

```usd
#usda 1.0
(
    defaultPrim = "Splat"
    metersPerUnit = 1
    upAxis = "Y"
)

def ParticleField3DGaussianSplat "Splat"
{
    point3f[] positions = [(0,0,0), (1,0,0)]
    float3[] scales = [(1,1,1), (1,1,1)]
    quatf[] orientations = [(1,0,0,0), (1,0,0,0)]
    float[] opacities = [0.5, 1.5]
    int radiance:sphericalHarmonicsDegree = 0
    float3[] radiance:sphericalHarmonicsCoefficients = [(0,0,0), (0,0,0)] (
        interpolation = "vertex"
        elementSize = 1
    )
    float3[] extent = [(-0.5,-0.5,-0.5), (1.5,0.5,0.5)]
}
```

### Invalid: Per-vertex array length mismatch

```usd
#usda 1.0
(
    defaultPrim = "Splat"
    metersPerUnit = 1
    upAxis = "Y"
)

def ParticleField3DGaussianSplat "Splat"
{
    point3f[] positions = [(0,0,0), (1,0,0)]
    float3[] scales = [(1,1,1)]
    quatf[] orientations = [(1,0,0,0), (1,0,0,0)]
    float[] opacities = [0.5, 0.5]
    int radiance:sphericalHarmonicsDegree = 0
    float3[] radiance:sphericalHarmonicsCoefficients = [(0,0,0), (0,0,0)] (
        interpolation = "vertex"
        elementSize = 1
    )
    float3[] extent = [(-0.5,-0.5,-0.5), (1.5,0.5,0.5)]
}
```

## How to comply

- Use OpenUSD **26.03+** (and Kit **110.1+** when applicable) when authoring or validating this schema
- Meet stage metadata expectations using the appropriate layout and units requirements for your delivery profile
- Author all required splat attributes with the same vertex count, opacities in [0, 1], positive scales, unit quaternion orientations, SH degree in {0,1,2,3}, matching `elementSize` on SH coefficients, and vertex interpolation on SH coefficients

## For More Information

- [UsdVol ParticleField3DGaussianSplat](https://openusd.org/release/api/class_usd_vol_particle_field3_d_gaussian_splat.html)
