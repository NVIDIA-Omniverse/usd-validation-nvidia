# dense-caption-capability-part

| Code          | DC.002                    |
|---------------|---------------------------|
| Version       | 1.0.0                     |
| Validator     |                           |
| Compatibility | {compatibility}`core-usd` |
| Tags          | {tag}`high-quality`       |

## Summary

Prims representing sub-objects or parts within the asset should be documented with additional dense captions.

## Description

**Root prims** of sub-objects or parts within the asset should contain documentation metadata, holding a Dense Caption string. This additional description helps identify parts of the asset with more detail.

## Why is it required?

- Dense captions provide richer semantic information useful for AI training and scene understanding.

## Examples

### Invalid: Part without dense captions

```usd
#usda 1.0

def XForm "SportCar" (
)
{
    def Mesh "ConvertibleTop"
    {
        ...
    }
}
```

### Valid: Part with dense captions

```usd
#usda 1.0

def XForm "SportCar" (
    doc = "This is red, two door sports car with a tan, leather interior and chrome wheels. The driver's window is up and the headlights are off."
)
{
    def Mesh "ConvertibleTop"
    {
        doc = "This is a retractable hard top."
    }
}
```

## How to comply

- Set the doc metadata string of part prims to dense captions. Python Snippet:

  ```python

  from pxr import Usd, UsdGeom

  # Get the root prim
  stage = Usd.Stage.Open("sportsCar.usd")
  root_prim = stage.GetPrimAtPath("/SportsCar/ConvertibleTop")
  root_prim.SetDocumentation("This is a retractable hard top.")

  ```



## For More Information

- [Documentation Metadata](https://openusd.org/dev/api/class_usd_object.html#a207a3fac40b4bd2dca8e9bce07d398e9)