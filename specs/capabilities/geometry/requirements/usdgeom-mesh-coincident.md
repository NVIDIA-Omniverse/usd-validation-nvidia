# usdgeom-mesh-coincident

| Code          | VG.008                              |
|---------------|-------------------------------------|
| Version       | 1.0.0                              |
| Validator     | {validator-latest-link}`scene-optimizer:vg-008` |
| Compatibility | {compatibility}`Core USD`          |
| Tags          | {tag}`performance`                 |

## Summary

Meshes should not share the exact same space

## Description

Each mesh should occupy its own unique space to ensure proper rendering and physics simulation. When multiple meshes need to share the same visual space, consider using visibility attributes so that only one mesh is visible at a time.

## Why is it required?
- Prevents visual artifacts (z-fighting)
- Maintains reliable physics simulation
- Optimizes raytracing performance
- Ensures efficient memory usage

## Examples

### Invalid: Coincident meshes

```usd
#usda 1.0

def Xform "CoincidentPlanes" {
    def Mesh "Plane1" {
        float3[] extent = [(-1, 0, -1), (1, 0, 1)]
        int[] faceVertexCounts = [4]
        int[] faceVertexIndices = [0, 1, 2, 3]
        point3f[] points = [(-1, 0, -1), (1, 0, -1), (1, 0, 1), (-1, 0, 1)]
    }

    def Mesh "Plane2" {
        # Exactly same position as Plane1
        float3[] extent = [(-1, 0, -1), (1, 0, 1)]
        int[] faceVertexCounts = [4]
        int[] faceVertexIndices = [0, 1, 2, 3]
        point3f[] points = [(-1, 0, -1), (1, 0, -1), (1, 0, 1), (-1, 0, 1)]
    }
}
```

### Valid: Meshes with proper spacing

```usd
#usda 1.0

def Xform "ProperlySpacedMeshes" {
    def Mesh "Plane1" {
        float3[] extent = [(-1, 0, -1), (1, 0, 1)]
        int[] faceVertexCounts = [4]
        int[] faceVertexIndices = [0, 1, 2, 3]
        point3f[] points = [(-1, 0, -1), (1, 0, -1), (1, 0, 1), (-1, 0, 1)]
    }

    def Mesh "Plane2" {
        # Offset in Y axis
        xformOp:translate = (0, 1, 0)
        token xformOpOrder = ["translate"]

        # Visibility is off
        hidden = true

        float3[] extent = [(-1, 0, -1), (1, 0, 1)]
        int[] faceVertexCounts = [4]
        int[] faceVertexIndices = [0, 1, 2, 3]
        point3f[] points = [(-1, 0, -1), (1, 0, -1), (1, 0, 1), (-1, 0, 1)]
    }
}
```

## How to comply
- Check for accidental duplicates
- Ensure proper spacing between meshes
- Review transform hierarchies
- Set coincident meshes to be hidden
- Fix in source application and re-convert

## For More Information
- [UsdGeom Mesh Documentation](https://openusd.org/release/api/class_usd_geom_mesh.html)