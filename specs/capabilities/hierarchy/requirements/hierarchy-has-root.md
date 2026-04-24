# hierarchy-has-root

| Code          | HI.001                    |
|---------------|---------------------------|
| Version       | 1.0.0                    |
| Validator     |                           |
| Compatibility | {compatibility}`OpenUSD`  |
| Tags          | {tag}`essential`         |

## Summary

Prim hierarchy must have a single root prim.

## Description

All prims that constitute the asset need to be descendants of the asset's default prim. Prims that are not part of the referenceable asset (e.g. review light rigs, cameras, or render var prims) are permitted outside that hierarchy.

## Why is it required?

- Ensures a single, clear entry point for the entire prim hierarchy
- Prevents orphaned prims which will not inherit transformation or visibility from the root prim
- Enables traversal and manipulation of the entire prim hierarchy

## Examples

### Valid: All Xforms under single root

```usd
#usda 1.0
(
    defaultPrim = "RootXform"
)
def Xform "RootXform"
{
    def Xform "Xform1"
    {
        def Xform "Child1" {}
    }

    def Xform "Xform2"
    {
        def Xform "Child2" {}
    }
}
```

### Valid: Prims that are not part of the referenceable asset are permitted

```usd
#usda 1.0
(
    defaultPrim = "Xform1"
)
def Xform "Xform1"
{
    def Xform "Child1" {}
}

def DomeLight "Light"
{
}
```

## How to comply

- Ensure all prims in the asset are descendants of a single root prim
- Avoid creating separate or disconnected prim hierarchies
- Maintain a clear and organized hierarchy structure
- Verify that all prims can be reached from the root prim

## For More Information

- [USD Hierarchy Documentation](https://openusd.org/release/api/class_usd_prim.html)
- [USD Stage Traversal](https://openusd.org/release/api/class_usd_stage.html)
