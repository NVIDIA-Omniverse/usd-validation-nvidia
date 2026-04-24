# usdgeom-mesh-normals-must-be-valid

| Code          | VG.028                    |
|---------------|---------------------------|
| Version       | 1.0.0                    |
| Validator     | {validator-latest-link}`scene-optimizer:vg-028` {oav-validator-latest-link}`vg-028` |
| Compatibility | {compatibility}`Core USD` |
| Tags          | {tag}`correctness`       |

## Summary

Mesh normals values must be valid to produce correct shading.

## Description

Mesh normals need to follow a set of conventions to produce correct shading results in most renderers:

- Sizes of normal arrays shall be consistent with the interpolation mode (faceVarying, vertex, uniform)
- Normals shall have a length of 1 within a tolerance of 1e-4 (including zero length, nan, inf etc)
- Normals must align with the front side of their contained face (ie, the normal should point outwards from the mesh as per the winding order)

## Why is it required?

- Incorrect normals may lead to incorrect shading results
- Incorrect normals may lead to incorrect simulation results
- Avoid confusion about the front/back side of the mesh

## Examples

### Invalid: Triangle with inconsistent winding order and normals

```usd
#usda 1.0
(
    metersPerUnit = 1.0
    upAxis = "Z"
)

def Mesh "InconsistentWindingOrder"
{
    point3f[] points = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
    int[] faceVertexCounts = [3]
    int[] faceVertexIndices = [0, 1, 2]  # CCW, so normal points +Z

    # Normal is set explicitly to point in the -Z direction
    normal3f[] normals = [(0, 0, -1)]
    uniform token normalsInterpolation = "faceVarying"
}

def Mesh "ConsistentWindingOrder"
{
    point3f[] points = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
    int[] faceVertexCounts = [3]
    int[] faceVertexIndices = [0, 1, 2]  # CCW, so normal points +Z

    # Normal is set explicitly to point in the -Z direction
    normal3f[] normals = [(0, 0, 1)]
    uniform token normalsInterpolation = "faceVarying"
}

# TODO: Example with 0 length normals, nan no
```

## How to comply

- Ensure that the normals are authored cleanly and correctly.
- As a developer of converters, ensure that the normals are correctly converted from the source format to the USD format or calculate normals correctly.

## For more information

- [USDGeom Documentation](https://openusd.org/docs/api/usd_geom_page_front.html#UsdGeom_WindingOrder)
