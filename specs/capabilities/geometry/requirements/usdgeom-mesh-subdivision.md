# usdgeom-mesh-subdivision

| Code          | VG.010                              |
|---------------|-------------------------------------|
| Version       | 1.0.0                              |
| Validator     | {oav-validator-latest-link}`vg-010` |
| Compatibility | {compatibility}`Core USD`          |
| Tags          | {tag}`performance`                 |

## Summary

Do not subdivide meshes with Normals.

## Description

In OpenUSD, mesh primitives have an attribute UsdGeom.Mesh->subdivisionScheme which defines the mesh subdivision behavior. If this attribute is unset the mesh will be subdivided by default, so it is important to set the value explicitly to "None" when subdivision is not required.

Meshes which are intended to be subdivided should not also provide surface normals. If the subdivision scheme is set and there are also surface normals, the surface normals will be ignored.

Subdivision should be used selectively to create smooth surfaces or enable displacement. Do not use subdivision when the mesh is already sufficiently tessellated.


## Why is it required?
Avoiding unnecessary subdivision enables:
- Faster "time to first pixel" (scene translation time)
- Optimized memory usage
- Improved rendering performance
- Better resource utilization for complex scenes

## Examples

### Invalid: Unnecessary subdivision on simple shape

```usd
#usda 1.0

def Mesh "OverSubdividedCube" {
    uniform token subdivisionScheme = "catmullClark"
    int[] faceVertexCounts = [4, 4, 4, 4, 4, 4]
    int[] faceVertexIndices = [0, 1, 2, 3, ...]
    normal3f[] normals = [(0,0,1), (0,0,1), (0,0,1), (0,0,1), ...] # Meshes that have normals should not have subdivision attributes
    point3f[] points = [(0,0,0), (1,0,0), (1,1,0), (0,1,0), ...]
}
```

### Valid: No subdivision for simple shape

```usd
#usda 1.0

def Mesh "SimpleCube" {
    uniform token subdivisionScheme = "none"
    int[] faceVertexCounts = [4, 4, 4, 4, 4, 4]
    int[] faceVertexIndices = [0, 1, 2, 3, ...]
    normal3f[] normals = [(0,0,1), (0,0,1), (0,0,1), (0,0,1), ...]
    point3f[] points = [(0,0,0), (1,0,0), (1,1,0), (0,1,0), ...]
}
```

## How to comply
- Set `subdivisionScheme` explicitly to None if subdivision is not required
- Fix in source application

## Validation
USD Validation NVIDIA includes a check that warns when meshes leave `subdivisionScheme` undefined, because the default value is `catmullClark` and may not be intended.

## For More Information
- [UsdGeom Mesh Documentation](https://openusd.org/release/api/class_usd_geom_mesh.html)
