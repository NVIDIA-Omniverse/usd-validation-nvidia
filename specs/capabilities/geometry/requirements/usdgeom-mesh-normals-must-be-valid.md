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

### Valid: Unit normals with each interpolation

```usd
#usda 1.0

def Mesh "VertexNormals"
{
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
    normal3f[] normals = [(0, 0, 1), (0, 0, 1), (0, 0, 1), (0, 0, 1)] (
        interpolation = "vertex"
    )
    uniform token subdivisionScheme = "none"
}

def Mesh "IndexedFaceVaryingNormals"
{
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
    normal3f[] primvars:normals = [(0, 0, 1), (1, 0, 0)] (
        interpolation = "faceVarying"
    )
    int[] primvars:normals:indices = [0, 0, 1, 1]
    uniform token subdivisionScheme = "none"
}

def Mesh "UniformNormals"
{
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
    normal3f[] normals = [(0, 0, 1)] (
        interpolation = "uniform"
    )
    uniform token subdivisionScheme = "none"
}

def Mesh "ConstantNormals"
{
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
    normal3f[] primvars:normals = [(0, 0, 1)] (
        interpolation = "constant"
    )
    uniform token subdivisionScheme = "none"
}
```

### Valid: Mesh without normals

```usd
#usda 1.0

def Mesh "QuadWithoutNormals"
{
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
    uniform token subdivisionScheme = "none"
}
```

### Valid: Subdivision mesh without normals

```usd
#usda 1.0

def Mesh "SubdivisionQuad"
{
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
    uniform token subdivisionScheme = "catmullClark"
}
```

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
```

### Invalid: Normals with non-finite components

```usd
#usda 1.0

def Mesh "QuadWithNonFiniteNormals"
{
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
    normal3f[] normals = [(0, 0, 1), (inf, 0, 1), (0, nan, nan), (0, 0, inf)] (
        interpolation = "vertex"
    )
    uniform token subdivisionScheme = "none"
}
```

### Invalid: Normals that are not unit length

```usd
#usda 1.0

def Mesh "QuadWithNonUnitNormals"
{
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
    normal3f[] normals = [(0, 0, 1), (1, 0, 1), (0, 1, 2), (0, 0, 177)] (
        interpolation = "vertex"
    )
    uniform token subdivisionScheme = "none"
}
```

### Invalid: Number of normals that does not match the interpolation

```usd
#usda 1.0

def Mesh "QuadWithMissingNormals"
{
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
    # Face-varying interpolation requires one normal per face corner
    normal3f[] normals = [(0, 0, 1), (0, 0, 1), (0, 0, 1)] (
        interpolation = "faceVarying"
    )
    uniform token subdivisionScheme = "none"
}
```

### Invalid: Normals on a subdivision mesh

```usd
#usda 1.0

def Mesh "SubdivisionQuadWithNormals"
{
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
    normal3f[] normals = [(0, 0, 1), (0, 0, 1), (0, 0, 1), (0, 0, 1)] (
        interpolation = "vertex"
    )
    uniform token subdivisionScheme = "catmullClark"
}
```

### Invalid: Normals on a mesh without a subdivision scheme

```usd
#usda 1.0

def Mesh "QuadWithNormalsAndNoScheme"
{
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
    # The subdivision scheme is not authored, so it is catmullClark
    normal3f[] normals = [(0, 0, 1), (0, 0, 1), (0, 0, 1), (0, 0, 1)] (
        interpolation = "vertex"
    )
}
```

## How to comply

- Ensure that the normals are authored cleanly and correctly.
- As a developer of converters, ensure that the normals are correctly converted from the source format to the USD format or calculate normals correctly.

## For more information

- [USDGeom Documentation](https://openusd.org/docs/api/usd_geom_page_front.html#UsdGeom_WindingOrder)
