# portable-asset-paths

| Code          | AA.003                              |
|---------------|-------------------------------------|
| Version       | 1.0.0                               |
| Validator     | {oav-validator-latest-link}`aa-003` |
| Compatibility | {compatibility}`core-usd`           |
| Tags          | {tag}`essential`                    |

## Summary

Asset paths should use forward slashes for cross-platform portability

## Description

Windows-style backslashes (`\`) in asset paths are not portable and can cause assets to fail loading on non-Windows platforms. USD expects forward slashes (`/`) as path separators regardless of the operating system. This requirement applies to all asset path types including sublayer paths, reference paths, payload paths, and asset attribute paths.

## Why is it required?

- Ensures assets can be loaded on any platform (Windows, Linux, macOS)
- Prevents path resolution failures when assets are shared across different operating systems
- Maintains consistency with USD's path handling conventions
- Avoids confusion with escape sequences in file formats

## Examples

### Valid: Sublayer path with forward slashes

```usd
#usda 1.0
(
    subLayers = [
        @./sublayers/materials.usda@
    ]
)
```

### Valid: Reference path with forward slashes

```usd
#usda 1.0

def Xform "Asset"
{
    def "Component" (
        references = @./components/part.usda@
    )
    {
    }
}
```

### Valid: Asset attribute path with forward slashes

```usd
#usda 1.0

def Material "MyMaterial"
{
    def Shader "diffuseTexture"
    {
        uniform token info:id = "UsdUVTexture"
        asset inputs:file = @./textures/diffuse.png@
        token outputs:rgb
    }
}
```

### Invalid: Sublayer path with backslashes

```usd
#usda 1.0
(
    subLayers = [
        @.\sublayers\materials.usda@
    ]
)
```

### Invalid: Reference path with backslashes

```usd
#usda 1.0

def Xform "Asset"
{
    def "Component" (
        references = @.\components\part.usda@
    )
    {
    }
}
```

### Invalid: Add reference path with backslashes

```usd
#usda 1.0

def Xform "Asset"
{
    def "Component" (
        add references = @.\components\part.usda@
    )
    {
    }
}
```

### Invalid: Asset attribute path with backslashes

```usd
#usda 1.0

def Material "MyMaterial"
{
    def Shader "diffuseTexture"
    {
        uniform token info:id = "UsdUVTexture"
        asset inputs:file = @.\textures\diffuse.png@
        token outputs:rgb
    }
}
```

## How to comply

- Always use forward slashes (`/`) as path separators in asset paths
- When exporting from Windows applications, ensure the exporter converts backslashes to forward slashes
- Use the automated fixer provided by the validator to convert existing backslashes to forward slashes
- Review any manually authored USD files for Windows-style paths

## For More Information

- [USD Glossary - Asset](https://openusd.org/release/glossary.html#asset) - USD terminology and concepts for assets
