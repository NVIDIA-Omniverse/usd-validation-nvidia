# material-preview-surface-specification

| Code          | VM.PS.001                              |
|---------------|----------------------------------------|
| Version       | 1.0.0                                 |
| Validator     | {oav-validator-latest-link}`vm-ps-001` |
| Compatibility | {compatibility}`Open USD`             |
| Tags          | {tag}`correctness`                    |

## Summary

Material attributes must comply with the UsdPreviewSurface specification to ensure consistent rendering and viewer compatibility.

## Description

All material attributes must strictly follow the UsdPreviewSurface specification, including:
- Parameter types must match the specification
- Token values must be from the allowed set
- Certain attributes must not contain time samples

## Why is it required?
- Inconsistent material behavior
- Rendering artifacts
- Incompatibility with USD viewers

## Examples

### Invalid: Non-compliant attributes

```usd
#usda 1.0

def Material "mtl_cube"
{
    def Shader "PreviewSurfaceTexture"
    {
        uniform token info:id = "UsdPreviewSurface"
        # Invalid: 'specular' connection not in specification
        float inputs:specular.connect = </World/Looks/mtl_cube/SpecularTex.outputs:r>
    }

    def Shader "diffuseColorTex"
    {
        uniform token info:id = "UsdUVTexture"
        # Invalid: 'bad' not in allowed tokens ['raw', 'sRGB', 'auto']
        uniform token inputs:sourceColorSpace = "bad"
    }
}
```

### Invalid: Wrong type and time-sampled tokens

```usd
#usda 1.0

def Material "mtl_sphere"
{
    def Shader "Shader"
    {
        uniform token info:id = "UsdPreviewSurface"
        # Invalid: Wrong type (color3f instead of float)
        color3f inputs:metallic = (0.5, 0.5, 0.5)
    }

    def Shader "roughnessTex"
    {
        uniform token info:id = "UsdUVTexture"
        # Invalid: Token attribute should not have time samples
        uniform token inputs:wrapT.timeSamples = {
            0: "invalid_wrap",
            1: "another_invalid"
        }
    }
}
```

### Valid: Compliant attributes

```usd
#usda 1.0

def Material "mtl_cube"
{
    token outputs:surface.connect = </World/Looks/mtl_cube/PreviewSurfaceTexture.outputs:surface>

    def Shader "PreviewSurfaceTexture"
    {
        uniform token info:id = "UsdPreviewSurface"
        float inputs:clearcoat = 0
        float inputs:clearcoatRoughness = 0
        color3f inputs:diffuseColor = (0.18, 0.18, 0.18)
        color3f inputs:diffuseColor.connect = </World/Looks/mtl_cube/diffuseColorTex.outputs:rgb>
        float inputs:displacement = 0
        float inputs:metallic.connect = </World/Looks/mtl_cube/metallicTex.outputs:r>
        normal3f inputs:normal.connect = </World/Looks/mtl_cube/normalTex.outputs:rgb>
        float inputs:roughness.connect = </World/Looks/mtl_cube/roughnessTex.outputs:r>
        token outputs:surface
    }

    def Shader "diffuseColorTex"
    {
        uniform token info:id = "UsdUVTexture"
        asset inputs:file = @./textures/color.jpg@
        string inputs:sourceColorSpace = "auto" (
            allowedTokens = ["auto", "raw", "sRGB"]
        )
        string inputs:wrapS = "useMetadata" (
            allowedTokens = ["black", "clamp", "repeat", "mirror", "useMetadata"]
        )
        string inputs:wrapT = "useMetadata" (
            allowedTokens = ["black", "clamp", "repeat", "mirror", "useMetadata"]
        )
        float2 inputs:st.connect = </World/Looks/mtl_cube/st.outputs:result>
        float3 outputs:rgb
    }
}
```

### Invalid: Connection to a parameter that is not in the specification

```usd
#usda 1.0

def Material "mtl_cube"
{
    token outputs:surface.connect = </mtl_cube/PreviewSurface.outputs:surface>

    def Shader "PreviewSurface"
    {
        uniform token info:id = "UsdPreviewSurface"
        # Invalid: 'specular' cannot be connected
        float inputs:specular.connect = </mtl_cube/roughnessTex.outputs:r>
        token outputs:surface
    }

    def Shader "roughnessTex"
    {
        uniform token info:id = "UsdUVTexture"
        float outputs:r
    }
}
```

### Invalid: Time-sampled token

```usd
#usda 1.0

def Material "mtl_cube"
{
    def Shader "roughnessTex"
    {
        uniform token info:id = "UsdUVTexture"
        # Invalid: Token values must not be time-sampled
        token inputs:wrapT.timeSamples = {
            0: "invalid_wrap",
            1: "another_invalid",
        }
        float outputs:r
    }
}
```

### Invalid: Wrong input type

```usd
#usda 1.0

def Material "mtl_cube"
{
    def Shader "PreviewSurface"
    {
        uniform token info:id = "UsdPreviewSurface"
        # Invalid: 'metallic' is a float
        color3f inputs:metallic = (0.5, 0.5, 0.5)
        token outputs:surface
    }
}
```

### Invalid: Wrong type of a connected input

```usd
#usda 1.0

def Material "mtl_cube"
{
    def Shader "PreviewSurface"
    {
        uniform token info:id = "UsdPreviewSurface"
        # Invalid: 'diffuseColor' is a color3f
        float3 inputs:diffuseColor.connect = </mtl_cube/diffuseColorTex.outputs:rgb>
        token outputs:surface
    }

    def Shader "diffuseColorTex"
    {
        uniform token info:id = "UsdUVTexture"
        float3 outputs:rgb
    }
}
```

### Invalid: Wrong output type

```usd
#usda 1.0

def Material "mtl_cube"
{
    def Shader "diffuseColorTex"
    {
        uniform token info:id = "UsdUVTexture"
        # Invalid: the 'rgb' output is a float3
        color3f outputs:rgb
    }
}
```

## How to comply
- Only use [core nodes](https://openusd.org/release/spec_usdpreviewsurface.html#core-nodes) as per the UsdPreviewSurface specification
- Only use allowed inputs and outputs as per the [UsdPreviewSurface specification](https://openusd.org/release/spec_usdpreviewsurface.html)

## For More Information
- [UsdPreviewSurface Specification](https://openusd.org/release/spec_usdpreviewsurface.html)
