# usdgeom-mesh-duplicate

| Code          | VG.022                              |
|---------------|-------------------------------------|
| Version       | 1.0.0                              |
| Validator     | {validator-latest-link}`scene-optimizer:vg-022` |
| Compatibility | {compatibility}`Core USD`          |
| Tags          | {tag}`performance`                 |

## Summary

Meshes should use instancing if they are identical apart from their world space location

## Description

Meshes that are identical apart from their location can be represented using instances, which means only one full copy of the mesh is stored, and all meshes can point to this instance.


```{note}
Ideally, instancing is applied at a higher level in the hierarchy to take full advantage of entire sub-hierarchies being instanced.
```

## Why is it required?
- Increased system and GPU memory usage
- Increased load times

## Examples

```usd
# Not recommended: Duplicate meshes
def Xform "World" {
    def Xform "DuplicatedMeshes" {
        def Mesh "Plane1" {
            # Offset in +Y
            double3 xformOp:translate = (0, 1, 0)
            uniform token[] xformOpOrder = ["translate"]

            float3[] extent = [(-1, 0, -1), (1, 0, 1)]
            int[] faceVertexCounts = [4]
            int[] faceVertexIndices = [0, 1, 2, 3]
            point3f[] points = [(-1, 0, -1), (1, 0, -1), (1, 0, 1), (-1, 0, 1)]
        }

        def Mesh "Plane2" {
            # Offset in -Y
            double3 xformOp:translate = (0, -1, 0)
            uniform token[] xformOpOrder = ["translate"]

            float3[] extent = [(-1, 0, -1), (1, 0, 1)]
            int[] faceVertexCounts = [4]
            int[] faceVertexIndices = [0, 1, 2, 3]
            point3f[] points = [(-1, 0, -1), (1, 0, -1), (1, 0, 1), (-1, 0, 1)]
        }
    }
}

# Recommended: Prototype with instances
def Xform "World" {
    def Xform "InstancedMeshes" {
        # Define a prototype mesh
        def Xform "PlaneProto" {
            def Mesh "Plane" {
                # Basic mesh data for a plane
                float3[] extent = [(-1, 0, -1), (1, 0, 1)]
                int[] faceVertexCounts = [4]
                int[] faceVertexIndices = [0, 1, 2, 3]
                point3f[] points = [(-1, 0, -1), (1, 0, -1), (1, 0, 1), (-1, 0, 1)]
            }
        }

        # Instance the prototype mesh
        def Xform "Plane1" (
            instanceable = true  # Mark as instanceable
            prepend references = </World/InstancedMeshes/PlaneProto> # Reference the prototype
        ) {
            # Apply transformation to instance
            double3 xformOp:translate = (0, 1, 0)
            uniform token[] xformOpOrder = ["xformOp:translate"]
        }

        # Instance the prototype mesh again
        def Xform "Plane2" (
            instanceable = true # Mark as instanceable
            prepend references = </World/InstancedMeshes/PlaneProto> # Reference the prototype
        ) {
            # Apply transformation to instance
            double3 xformOp:translate = (0, -1, 0)
            uniform token[] xformOpOrder = ["xformOp:translate"]
        }
    }
}
```

## How to comply
- Check for duplicated geometry
- Ensure instancing is used when meshes are identical but in different world space locations
- Fix in source application and re-convert

## For More Information
- [UsdGeom Mesh Documentation](https://openusd.org/release/api/class_usd_geom_mesh.html)
- [USD Scenegraph Instancing](https://openusd.org/release/api/_usd__page__scenegraph_instancing.html)
