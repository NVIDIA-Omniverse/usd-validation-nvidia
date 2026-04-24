# material-duplicates

| Code          | VM.D.001                              |
|---------------|--------------------------------------|
| Version       | 1.0.0                               |
| Validator     | {oav-validator-latest-link}`vm-d-001` |
| Compatibility | {compatibility}`Open USD`          |
| Tags          | {tag}`performance`                 |

## Summary

Using fewer materials can result in better performance.

## Description

Duplicating materials can impact performance. Materials should be reused for multiple assignments when possible.

In some cases, it may be desirable or necessary to duplicate materials:

- to retain the ability to manipulate specific attributes
- to conform to instance encapsulation requirements
- to conform to payload encapsulation requirements ( VM.BIND.001 )

## Why is it required?

Unnecessarily duplicated materials are non-intuitive and inefficient for users, as any shared modifications to materials also have to be duplicated.
Duplicate materials may cause:

- Higher memory usage and slower file loading (see [Maximizing USD Performance](https://openusd.org/release/maxperf.html) > Minimize Prim Count)
- Larger file sizes
- Longer time to first pixel (scene translation for rendering) due to increased material de-duplication cost

## Examples

### Invalid: Duplicate materials

```usd
#usda 1.0

def Cube "Cube1" (
    prepend apiSchemas = ["MaterialBindingAPI"]
)
{
    float3[] extent = [(-1, -1, -1), (1, 1, 1)]
    rel material:binding = </Material1>
    double size = 2
}

def Material "Material1"
{
    token outputs:displacement.connect = </Material1/Shader.outputs:displacement>
    token outputs:surface.connect = </Material1/Shader.outputs:surface>

    def Shader "Shader"
    {
        uniform token info:id = "UsdPreviewSurface"
        color3f inputs:diffuseColor = (1, 1, 0)
        token outputs:displacement
        token outputs:surface
    }
}

def Cube "Cube2" (
    prepend apiSchemas = ["MaterialBindingAPI"]
)
{
    float3[] extent = [(-1, -1, -1), (1, 1, 1)]
    rel material:binding = </Material2>
    double size = 2
}

def Material "Material2"
{
    token outputs:displacement.connect = </Material2/Shader.outputs:displacement>
    token outputs:surface.connect = </Material2/Shader.outputs:surface>

    def Shader "Shader"
    {
        uniform token info:id = "UsdPreviewSurface"
        color3f inputs:diffuseColor = (1, 1, 0)
        token outputs:displacement
        token outputs:surface
    }
}
```

### Valid: Reusing the same material

```usd
#usda 1.0

def Cube "Cube1" (
    prepend apiSchemas = ["MaterialBindingAPI"]
)
{
    float3[] extent = [(-1, -1, -1), (1, 1, 1)]
    rel material:binding = </Material>
    double size = 2
}

def Cube "Cube2" (
    prepend apiSchemas = ["MaterialBindingAPI"]
)
{
    float3[] extent = [(-1, -1, -1), (1, 1, 1)]
    rel material:binding = </Material>
    double size = 2
}

def Material "Material"
{
    token outputs:displacement.connect = </Material/Shader.outputs:displacement>
    token outputs:surface.connect = </Material/Shader.outputs:surface>

    def Shader "Shader"
    {
        uniform token info:id = "UsdPreviewSurface"
        color3f inputs:diffuseColor = (1, 1, 0)
        token outputs:displacement
        token outputs:surface
    }
}
```

## How to comply
- Consider instancing materials - see: [Instancing — Omniverse USD](https://docs.omniverse.nvidia.com/usd/latest/learn-openusd/independent/modularity-guide/instancing.html#material-instances)

## For More Information
- [USD Material Documentation](https://openusd.org/release/api/usd_shade_page_front.html)
