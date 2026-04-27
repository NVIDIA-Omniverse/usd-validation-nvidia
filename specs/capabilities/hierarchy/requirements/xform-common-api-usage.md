# xform-common-api-usage

| Code          | HI.005                    |
|---------------|---------------------------|
| Version       | 1.0.0                    |
| Validator     |                           |
| Compatibility | {compatibility}`OpenUSD`  |
| Tags          | {tag}`correctness`       |

## Summary

Transformations on prims representing objects or groups that require placement should conform to the UsdGeomXformCommonAPI.

## Description

`UsdGeomXformCommonAPI` provides a standardized interface for authoring common transformation operations. Developers are encouraged to avoid direct manipulation of the xformOpOrder and individual xformOp attributes unless advanced control is explicitly required.

If a prim is not intended to be translated, rotated, or scaled by users, the recommended alternatives are:

1. UsdGeomXformCommonAPI (e.g. ["xformOp:translate", "xformOp:translate:pivot", "xformOp:rotateXYZ", "xformOp:scale", "!invert!xformOp:translate:pivot"])
2. Transform Matrix (e.g. ["xformOp:transform"])
3. Translate + Quaternion (e.g. ["xformOp:translate", "xformOp:orient"])

## Why is it required?

- Avoids the need to manually decompose the transform matrix into translation, rotation and scale components when human readable values are required.
- Provides a consistent transformation description when composing transforms from multiple USD layers.
-
## Examples

### Recommended: Using UsdGeomXformCommonAPI

```usd
#usda 1.0

def Xform "Door" ()
{
    def Scope "Geometry" {
        def Xform "Panel" {
            float3 xformOp:translate = (0.0, 0.0, 0.0)
            float3 xformOp:rotateXYZ = (0.0, 0.0, -45.0)
            float3 xformOp:scale = (1.0, 1.0, 1.0)
            uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ", "xformOp:scale"]
        }
    }
}
```

### Not recommended: Usage of transform xformOp for prims that are not intended to be translated, rotated or scaled by users

```usd
#usda 1.0

def Xform "Door_NonRecommended" ()
{
    def Scope "Geometry" {
        def Xform "Panel" {
            matrix4d xformOp:transform = ((0.70710678, -0.70710678, 0, 0), (0.70710678, 0.70710678, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))
            uniform token[] xformOpOrder = ["xformOp:transform"]
        }
    }
}
```

## How to comply

- Use the UsdGeomXformCommonAPI to author transformations on prims that are intended to be translated, rotated or scaled by users (e.g. the root prim of an asset)
- Use the standard translate, rotate, scale, pivot and inverse pivot attributes provided by the API
- Avoid direct manipulation of xformOpOrder unless advanced control is needed

## For more information

- [UsdGeomXformCommonAPI Documentation](https://openusd.org/release/api/class_usd_geom_xform_common_a_p_i.html)
- [USD Transform Operations](https://openusd.org/release/api/class_usd_geom_xformable.html)

## Utility Script

The script below will convert xformOp:transform to UsdGeomXformCommonAPI xform Ops.

Note: The xformOp:transform attributes should be defined in the current edit target to that the script can remove them.

```python

"""
OpenUSD Script: Convert Transform Ops to TRS (Translate, Rotate, Scale) Ops
Using UsdGeomXformCommonAPI

This script converts transform xform ops (matrix4d) on USD prims to the standard
TRS format supported by XformCommonAPI using the built-in GetXformVectors() and
SetXformVectors() methods that handle all the matrix decomposition automatically.
"""

from pxr import Usd, UsdGeom, Gf, Sdf
import omni.usd

def convert_prim_to_trs(prim, time_samples=None, rotation_order=UsdGeom.XformCommonAPI.RotationOrderXYZ):
    """
    Convert a prim's transform operations to TRS format using XformCommonAPI.

    Args:
        prim: UsdPrim to convert
        time_samples: List of time codes to sample, or None for default time
        rotation_order: UsdGeom.XformCommonAPI.RotationOrder enum value

    Returns:
        bool: True if conversion was successful, False otherwise
    """
    if not prim.IsValid():
        print(f"Error: Invalid prim {prim.GetPath()}")
        return False

    # Check if prim is transformable
    if not UsdGeom.Xformable(prim):
        print(f"Warning: Prim {prim.GetPath()} is not transformable, skipping")
        return True

    xformable = UsdGeom.Xformable(prim)

    # Create XformCommonAPI
    xform_api = UsdGeom.XformCommonAPI(prim)

    # Check if prim has any matrix transform ops that need conversion
    existing_ops = xformable.GetOrderedXformOps()
    has_matrix_op = any(op.GetOpType() == UsdGeom.XformOp.TypeTransform for op in existing_ops)

    if not has_matrix_op:
        print(f"Info: Prim {prim.GetPath()} has no matrix transform ops, skipping")
        return True

    # Get time codes to process
    time_codes = time_samples if time_samples else [Usd.TimeCode.Default()]

    print(f"Converting prim {prim.GetPath()} to TRS format...")

    # First, read all the transform data for each time sample
    transform_data = {}

    # Process each time sample to get the data
    for time_code in time_codes:
        # Use GetXformVectors to extract TRS components - this handles all the matrix decomposition!
        # The function returns a tuple of (translation, rotation, scale, pivot, rotation_order)
        try:
            result = xform_api.GetXformVectors(time_code)
            if not result:
                print(f"Warning: Failed to get xform vectors for {prim.GetPath()} at time {time_code}")
                continue

            translation, rotation, scale, pivot, rotation_order_out = result
            transform_data[time_code] = (translation, rotation, scale, pivot, rotation_order_out)

        except Exception as e:
            print(f"Warning: Exception getting xform vectors for {prim.GetPath()} at time {time_code}: {e}")
            continue

    # Now clear existing transform ops and delete the old matrix transform ops
    existing_ops = xformable.GetOrderedXformOps()
    for op in existing_ops:
        print(op)
        if op.GetOpType() == UsdGeom.XformOp.TypeTransform:
            # Remove the transform op attribute entirely
            prim.RemoveProperty(op.GetAttr().GetName())

    xformable.ClearXformOpOrder()

    # Set the new TRS ops for each time sample
    for time_code, (translation, rotation, scale, pivot, rotation_order_out) in transform_data.items():

        # Clear existing xform ops and set new TRS ops
        # SetXformVectors will create the proper TRS op structure
        success = xform_api.SetXformVectors(
            translation, rotation, scale, pivot, rotation_order, time_code
        )

        if not success:
            print(f"Warning: Failed to set xform vectors for {prim.GetPath()} at time {time_code}")
            continue

    print(f"Successfully converted {prim.GetPath()} to TRS format")
    return True

def convert_stage_to_trs(stage, prim_paths=None, time_samples=None, rotation_order=UsdGeom.XformCommonAPI.RotationOrderXYZ):
    """
    Convert all or specified prims in a stage to TRS format.

    Args:
        stage: UsdStage to process
        prim_paths: List of prim paths to convert, or None for all transformable prims
        time_samples: List of time codes to sample
        rotation_order: Rotation order to use for conversions

    Returns:
        int: Number of prims successfully converted
    """
    if not stage:
        print("Error: Invalid stage")
        return 0

    converted_count = 0

    if prim_paths:
        # Convert specific prims
        for path_str in prim_paths:
            prim_path = Sdf.Path(path_str)
            prim = stage.GetPrimAtPath(prim_path)

            if convert_prim_to_trs(prim, time_samples, rotation_order):
                converted_count += 1
    else:
        # Convert all prims with matrix transform ops
        for prim in stage.Traverse():
            if UsdGeom.Xformable(prim):
                xformable = UsdGeom.Xformable(prim)
                existing_ops = xformable.GetOrderedXformOps()
                has_matrix_op = any(op.GetOpType() == UsdGeom.XformOp.TypeTransform for op in existing_ops)

                if has_matrix_op and convert_prim_to_trs(prim, time_samples, rotation_order):
                    converted_count += 1

    return converted_count

# Example usage in Omniverse Script Editor:
# Get the current stage
stage = omni.usd.get_context().get_stage()

# Convert all prims with matrix transform ops to TRS format
if stage:
    print("Converting all prims with matrix transform ops to TRS format...")
    converted_count = convert_stage_to_trs(stage)
    print(f"Successfully converted {converted_count} prims to TRS format")
else:
    print("Error: No stage available")

# Or convert specific prims:
# convert_prim_to_trs(stage.GetPrimAtPath("/World/Cube"))

# Or convert with specific rotation order:
# convert_stage_to_trs(stage, rotation_order=UsdGeom.XformCommonAPI.RotationOrderZXY)
```