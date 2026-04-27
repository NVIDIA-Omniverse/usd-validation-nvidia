# usdgeom-mesh-identical-timesamples

| Code          | VG.015                              |
|---------------|-------------------------------------|
| Version       | 1.0.0                              |
| Validator     | {validator-latest-link}`scene-optimizer:vg-015` |
| Compatibility | {compatibility}`Core USD`          |
| Tags          | {tag}`performance`                 |

## Summary

Use time samples only when attribute values change

## Why is it required?

- Improves playback performance
- Ensures memory efficiency
- Optimizes data storage and transmission

  While binary ["crate"](https://openusd.org/release/glossary.html#crate-file-format) USD layers may reduce the impact through de-duplication, avoiding redundant time samples ensures optimal performance across all downstream systems, including renderers that may not perform the same de-duplication.

## Examples

### Invalid: Identical time samples

```usd
#usda 1.0

def Mesh "MeshWithIdenticalTimeSamples" {
    uniform token subdivisionScheme = "none"
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points.timeSamples = {
        1: [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)],
        2: [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)]
    }
}
```

### Valid: No time samples

```usd
#usda 1.0

def Mesh "MeshWithoutTimeSamples" {
    uniform token subdivisionScheme = "none"
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)]
}
```

### Invalid: Some identical time samples

```usd
#usda 1.0

def Mesh "MeshWithSomeIdenticalTimeSamples" {
    uniform token subdivisionScheme = "none"
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points.timeSamples = {
        1: [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)],
        2: [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)],
        3: [(1.0, 0.0, 0.0), (2.0, 0.0, 0.0), (2.0, 1.0, 0.0), (1.0, 1.0, 0.0)],
        4: [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)]
    }
}
```

### Valid: No sequential identical time samples

```usd
#usda 1.0

def Mesh "MeshWithoutIdenticalTimeSamples" {
    uniform token subdivisionScheme = "none"
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points.timeSamples = {
        2: [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)],
        3: [(1.0, 0.0, 0.0), (2.0, 0.0, 0.0), (2.0, 1.0, 0.0), (1.0, 1.0, 0.0)],
        4: [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)]
    }
}
```

### Invalid: Only one time sample

```usd
#usda 1.0

def Mesh "MeshWithOneTimeSample" {
    uniform token subdivisionScheme = "none"
    int[] faceVertexCounts = [4]
    int[] faceVertexIndices = [0, 1, 2, 3]
    point3f[] points.timeSamples = {
        1: [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)]
    }
}
```

## How to comply
- Remove animation (time samples) from static attributes / meshes
- Remove redundant time samples from animated meshes, for example with the [Scene Optimizer in Omniverse](https://docs.omniverse.nvidia.com/extensions/latest/ext_scene-optimizer/operations.html#optimize-time-samples)
- For developers: Use [UsdUtilsSparseValueWriter](https://openusd.org/release/api/class_usd_utils_sparse_value_writer.html) to write time samples in a sparse manner.
- For Meshes with only one time sample, validators should warn and offer to move the time sample to the default field of the layer. Remaining time samples should be blocked or removed to avoid accidentally exposing a weaker opinion.
