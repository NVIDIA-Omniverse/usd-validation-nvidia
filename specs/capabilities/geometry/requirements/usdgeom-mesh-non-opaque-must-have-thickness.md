# usdgeom-mesh-non-opaque-must-have-thickness

| Code          | VG.031                    |
|---------------|---------------------------|
| Version       | 1.0.0                    |
| Validator     |                           |
| Compatibility | {compatibility}`Core USD` |
| Tags          | {tag}`correctness`       |


## Summary

Meshes made from non opaque materials shall have thickness

## Description

Raytraced visualization of non opaque materials necessetates that the rendered geometric body has thickness, so that refraction and transmission can be calculated with sufficient accuracy. Thin / single sided meshes will not appear correct.

Ensure that meshes that represent non-opaque objects have faces "on both sides" and that their winding order correctly denotes their orientation.  

```{note}
This requirement does not relate to thin surfaces such as paper or leaves.
```

## Why is it required ?

- Accurate shading of transmission requires thickness
- Accurate shading of refraction requires thickness


## How to comply

- Model non-opaque meshes to be watertight / have "thickness"
- When optimizing, take care to not remove interior faces from non-opaque objects
