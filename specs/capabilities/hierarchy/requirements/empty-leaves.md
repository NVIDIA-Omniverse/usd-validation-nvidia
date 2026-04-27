# empty-leaves

| Code          | HI.012                    |
|---------------|---------------------------|
| Version       | 1.0.0                    |
| Validator     | {validator-latest-link}`scene-optimizer:vg-012` |
| Compatibility | {compatibility}`OpenUSD`  |
| Tags          | {tag}`performance`       |

## Summary

Avoid empty leaf nodes in scene hierarchy

## Description

Empty leaf nodes take up space and add complexity to the scene. Remove any empty leaf nodes that are not required. Empty leaf nodes can include for example xforms, scopes, general grouping prims, empty geometry prims.

## Why is it required?

- Improves scene size, load time and memory usage.

## Examples

### Invalid: Unnecessary, empty leaf prims

```usd

#usda 1.0
(
    defaultPrim = "root"
)

def Xform "root"
{
    def Xform "World"
    {
        def Xform "Leaf1" {}

        def Xform "Leaf2"
        {
            def Xform "Leaf1" {}
            def Xform "Leaf2" {}
            def Scope "Leaf3" {}
        }

        def Xform "Leaf3" {}

        def Xform "NotLeaf1"
        {
            def Xform "Leaf1" {}

            def Xform "NotLeaf1" {
                def Mesh "Mesh1" {}
            }
        }

        def Xform "Leaf4"
        {
            def Xform "XformRefChild" {}
        }

        def Xform "NotLeaf2"
        {
            def Xform "NotLeaf1" {
                def Mesh "Mesh1" {}
            }
        }
    }
    def Xform "Leaf1" {}
}

```

### Valid: Prim hierarchy without unnecessary leaf prims


```usd

#usda 1.0
(
    defaultPrim = "root"
)

def Xform "root"
{
    def Xform "World"
    {

        def Xform "NotLeaf1"
        {
            def Xform "NotLeaf1" {
                def Mesh "Mesh1" {}
            }
        }

        def Xform "NotLeaf2"
        {
            def Xform "NotLeaf1" {
                def Mesh "Mesh1" {}
            }
        }
    }
}
```


## How to comply

- Remove empty leaf nodes.
- The Omniverse [Scene Optimizer provides an operation called "Prune Leaves"](https://docs.omniverse.nvidia.com/extensions/latest/ext_scene-optimizer/operations.html#so-prune-leaf) that can be used to remove empty leaf nodes.


## For More Information

- [USD Stage Traversal](https://openusd.org/release/api/class_usd_stage.html)
