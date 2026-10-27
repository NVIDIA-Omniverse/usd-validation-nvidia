# usdgeom-mesh-winding-order

| Code          | VG.029                    |
|---------------|---------------------------|
| Version       | 1.0.0                    |
| Validator     | {validator-latest-link}`scene-optimizer:vg-029` {oav-validator-latest-link}`vg-029` |
| Compatibility | {compatibility}`Core USD` |
| Tags          | {tag}`correctness`       |

## Summary

The winding order of faces in a mesh must correctly represent the orientation (front/back) of the face.

## Description

In order to correctly represent the orientation (front/back) of a face, the winding order of faces in a mesh must be correct. In OpenUSD, the winding order is defined by the `faceVertexIndices` array of a mesh and is running in counter-clockwise (CCW) order.

## Why is it required?

Visualization, culling and other algorithms rely on correct winding order to determine the front/back sides of a mesh. For example, when calculating shadows. Surface normals, which are used primarily for shading, should be consistent with the winding order to avoid potential artifacts.

## Examples

In these examples the counter-clockwise winding of the quad faces towards +Z.

### Valid: Normals consistent with the winding order

```usd
#usda 1.0

def Mesh "Quad"
{
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
    normal3f[] normals = [(0, 0, 1), (0, 0, 1), (0, 0, 1), (0, 0, 1)] (
        interpolation = "faceVarying"
    )
}
```

### Valid: Per-vertex normals consistent with the winding order

```usd
#usda 1.0

def Mesh "Quad"
{
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
    normal3f[] normals = [(0, 0, 1), (0, 0, 1), (0, 0, 1), (0, 0, 1)] (
        interpolation = "varying"
    )
}
```

### Valid: Left-handed orientation with normals that agree with it

```usd
#usda 1.0

def Mesh "Quad"
{
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
    normal3f[] normals = [(0, 0, -1), (0, 0, -1), (0, 0, -1), (0, 0, -1)] (
        interpolation = "faceVarying"
    )
    uniform token orientation = "leftHanded"
}
```

### Valid: Winding check skips a mesh without normals

```usd
#usda 1.0

def Mesh "Quad"
{
    # Without normals there is nothing to compare with the winding order
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]

}
```

### Valid: Normals that do not match the topology

```usd
#usda 1.0

def Mesh "Quad"
{
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
    # Reported for the normals, not for the winding order
    normal3f[] normals = [(0, 0, -1)] (
        interpolation = "faceVarying"
    )
}
```

### Valid: Indexed normals with indices that are out of range

```usd
#usda 1.0

def Mesh "Quad"
{
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
    # Reported for the normals, not for the winding order
    normal3f[] primvars:normals = [(0, 0, -1)] (
        interpolation = "faceVarying"
    )
    int[] primvars:normals:indices = [0, 0, 0, 1]
}
```

### Invalid: Inconsistent winding order

```{figure} /specs/_static/images/winding_order.jpg

Visual artifacts when the winding order is incorrect in Storm.
```

```usd
#usda 1.0
# Invalid: Cube with flipped winding order for the top face
(
    metersPerUnit = 1.0
    upAxis = "Z"
)

def Xform "World"
{
    def Mesh "Cube"
    {
        point3f[] points = [(-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5), (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5)]
        int[] faceVertexCounts = [4, 4, 4, 4, 4, 4]
        # Outward normals, one per face corner
        normal3f[] normals = [
            (0, 0, -1), (0, 0, -1), (0, 0, -1), (0, 0, -1),
            (0, 1, 0), (0, 1, 0), (0, 1, 0), (0, 1, 0),
            (1, 0, 0), (1, 0, 0), (1, 0, 0), (1, 0, 0),
            (0, -1, 0), (0, -1, 0), (0, -1, 0), (0, -1, 0),
            (-1, 0, 0), (-1, 0, 0), (-1, 0, 0), (-1, 0, 0),
            (0, 0, 1), (0, 0, 1), (0, 0, 1), (0, 0, 1)
        ] (
            interpolation = "faceVarying"
        )

        # Indices for each quad face, CCW by default
        # Let's flip the winding order for the top face (face 5)
        int[] faceVertexIndices = [
            0, 1, 2, 3,      # Bottom (-Z)
            3, 2, 6, 7,      # Front (+Y)
            2, 1, 5, 6,      # Right (+X)
            1, 0, 4, 5,      # Back (-Y)
            0, 3, 7, 4,      # Left (-X)
            4, 7, 6, 5       # Top (+Z) -- FLIPPED WINDING
        ]
    }
}

```

### Invalid: Indexed normals opposite to the winding order

```usd
#usda 1.0

def Mesh "Quad"
{
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
    # Every corner uses the last value, which points towards -Z
    normal3f[] primvars:normals = [(0, 0, 1), (0, 0, 1), (0, 0, 1), (0, 0, -1)] (
        interpolation = "faceVarying"
    )
    int[] primvars:normals:indices = [3, 3, 3, 3]
}
```

### Invalid: Right-handed orientation with normals opposite to the winding order

```usd
#usda 1.0

def Mesh "Quad"
{
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
    normal3f[] normals = [(0, 0, -1), (0, 0, -1), (0, 0, -1), (0, 0, -1)] (
        interpolation = "faceVarying"
    )
    uniform token orientation = "rightHanded"
}
```

### Invalid: Per-vertex normals opposite to the winding order

```usd
#usda 1.0

def Mesh "Quad"
{
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
    normal3f[] normals = [(0, 0, -1), (0, 0, -1), (0, 0, -1), (0, 0, -1)] (
        interpolation = "varying"
    )
}
```

### Invalid: Left-handed orientation with normals opposite to it

```usd
#usda 1.0

def Mesh "Quad"
{
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
    normal3f[] normals = [(0, 0, 1), (0, 0, 1), (0, 0, 1), (0, 0, 1)] (
        interpolation = "varying"
    )
    uniform token orientation = "leftHanded"
}
```

