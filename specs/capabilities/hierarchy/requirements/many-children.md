# many-children

| Code          | HI.011                    |
|---------------|---------------------------|
| Version       | 1.0.0                    |
| Validator     | {validator-latest-link}`scene-optimizer:vg-011` |
| Compatibility | {compatibility}`OpenUSD`  |
| Tags          | {tag}`performance`       |

## Summary

Avoid large numbers of child prims under a parent xform

## Description

Many sibling prims can be expensive to traverse and are hard to navigate from a scene organization perspective. Users benefit when assets are organized into manageable groups rather than a flat sibling list, for example when authoring opinions or animation. Ie, in the example below, consider that the user may want to hide or rotate the lid and how this would be facilitated in a flat vs nested hierarchy.


 ## Why is it required?

- Improves scene organization
- Improves traversal time

## Examples

### Not recommended: Many children under a single prim

```usd
#usda 1.0

def Xform "World" () {
    def Mesh "Mesh1" () {}
    def Mesh "Mesh2" () {}
    def Mesh "Mesh3" () {}
    def Mesh "Mesh4" () {}
    def Mesh "Mesh5" () {}
}
```

### Recommended: Children distributed among multiple prims

```usd
#usda 1.0

def Xform "Toolbox" () {
    def Scope "Base" () {
        def Mesh "Outter_shell" () {}
        def Mesh "Inner_shell" () {}
    }


    def Xform "Lid" () {
        def Mesh "Cover" () {}

        def Mesh "Handle" () {}

        def Scope "Locks" () {
            def Mesh "Lock_left" () {}
            def Mesh "Lock_right" () {}
        }

    }
}

```


## How to comply

- Reorganize scene to place fewer prims under one parent.

## For More Information

- [USD Stage Traversal](https://openusd.org/release/api/class_usd_stage.html)
- [Principles of Scalable Asset Structure in OpenUSD](https://docs.omniverse.nvidia.com/usd/latest/learn-openusd/independent/asset-structure-principles.html)
