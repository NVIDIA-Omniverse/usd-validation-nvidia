# stage-has-default-prim

| Code          | HI.004                              |
|---------------|-------------------------------------|
| Version       | 1.0.0                              |
| Validator     | {oav-validator-latest-link}`hi-004` |
| Compatibility | {compatibility}`OpenUSD`           |
| Tags          | {tag}`essential`                   |

## Summary

Stage must specify a default prim to define the root entry point.

## Description

The stage must have a valid defaultPrim specified in the stage metadata. This defines which prim should be considered the root or entry point of the stage. The default prim is used by various tools and systems to determine where to start traversing the stage hierarchy.

## Why is it required?

- Provides a consistent entry point for stage traversal
- Required by many USD tools and systems
- Helps with stage composition, assembly and referencing
- Essential for proper stage organization

## Examples

### Invalid: No defaultPrim specified

```usd
#usda 1.0
(
    metersPerUnit = 0.01
)

def Xform "World"
{
    def Cube "MyCube"
    {
        double size = 1.0
    }
}
```

### Valid: defaultPrim specified

```usd
#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1.0
)

def Xform "World"
{
    def Cube "MyCube"
    {
        double size = 1.0
    }
}
```

## How to comply

- Set stage defaultPrim value in the stage metadata
- Ensure the specified prim exists in the stage

## For More Information

- [USD Stage Documentation](https://openusd.org/release/api/class_usd_stage.html)
- [USD Stage Metadata Documentation](https://openusd.org/release/api/class_sdf_layer.html)
