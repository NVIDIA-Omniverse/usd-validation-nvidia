# dense-caption-capability

| Code          | DC.001                    |
|---------------|---------------------------|
| Version       | 1.0.0                     |
| Validator     |                           |
| Compatibility | {compatibility}`core-usd` |
| Tags          | {tag}`essential`          |

## Summary

The Root Prim must inlcude documentation metadata that describes the 3D Asset.

## Description

The **root prim** of the asset **must** contain documentation metadata, holding a Dense Caption string. This additional description helps identify the asset with more detail than semantic labels.

## Why is it required?

- Dense captions provide richer semantic information useful for AI training and scene understanding.

## Examples

### Invalid: No dense caption

```usd
#usda 1.0

def XForm "SportCar" (
)
{
    ...
}
```

### Valid: Dense caption

```usd
#usda 1.0

def XForm "SportCar" (
    doc = "This is a red, two door sports car with a tan, leather interior and chrome wheels. The driver's window is up and the headlights are off."
)
{
    ...
}
```

## How to comply

- Set the doc metadata string of the root prim to a dense caption. Python Snippet:

  ```python

  from pxr import Usd, UsdGeom

  # Get the root prim
  stage = Usd.Stage.Open("sportsCar.usd")
  root_prim = stage.GetPrimAtPath("/SportsCar")
  root_prim.SetDocumentation("This is a dense caption that describes the asset.")

  ```



## For More Information

- [Documentation Metadata](https://openusd.org/dev/api/class_usd_object.html#a207a3fac40b4bd2dca8e9bce07d398e9)