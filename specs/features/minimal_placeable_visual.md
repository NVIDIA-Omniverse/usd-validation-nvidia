# Minimal Placeable Visual

| **Property**            | **Value**         |
|-------------------------|-------------------|
| Version                 | 1.0.0             |
| Dependency              | OpenUSD           |

<!-- | Asset Class             | `Prop`            | -->
<!-- | Supported Visualization | `Minimal Placeable Visual`  | -->
<!-- | Proprietary Techs       | `None`            | -->

## Description

The minimal placeable visual feature comprises a list of requirements that enable the digital representation of a real world object to be visualized in a broad range of applications.

It additionally provides a list of requirements to ensure that the scale, units and placement of the object may be correctly represented, so that the object can be placed and aggregated with other objects in a scene.


```{figure} /specs/_static/minimal_placeable_visual/minimal_placeable_visual.gif
:name: fig-minimal_placeable_visual

Fig 1: Visualization of a simple asset in NVIDIA Omniverse to demonstrate the capabilities of the minimal placeable visual feature.

For details, see [Runtime Testing](#runtime-testing).
```


<!--
## Specification

This feature is based on the [Specification for Asset Geometry](../specifications/specification_for_asset_geometry.1.0.0.md)
-->


## Requirements

```{features-table}
  HI.001
  HI.004
  HI.003
  UN.006
  UN.007
  VG.002
  VG.025
  VG.028
  VG.027
  VG.014
  VG.029
  VG.MESH.001
```



## Runtime Testing

To verify this feature, the following runtime testing requirements should be met.



```{list-table} Runtime Testing Requirements
:header-rows: 1
:widths: 25 15 60

* - Category
  - Requirement ID
  - Description
* - Loading and Display
  - AA.002
  - Not strictly required as a part of this feature, but a good baseline test to have in all runtime testing. The asset loads into a runtime environment without errors or warnings related to unsupported schemas or invalid data. *Asset is loaded into stage, no framing camera framing is performed*
* - Loading and Display
  - VG.001, VG.002
  - The asset's geometry is visible and can be automatically framed by the viewport's perspective camera, indicating a valid and computable bounding box. *Camera is automatically framed*
* - Coordinate System and Scale
  - UN.001, UN.006
  - When referenced into a stage with upAxis set to 'Z', the asset appears with the correct "up" direction. *"up arrow" gizmo is positioned next to the asset*
* - Coordinate System and Scale
  - UN.002, UN.007
  - When referenced into a stage with metersPerUnit set to 1.0, the asset appears at its correct, real-world physical scale (e.g., a 2-meter tall object is 2 units high in the scene). *Scale reference asset (human silhouette) is positioned next to the asset*
* - Transformation and Pivot Point
  - HI.001, HI.003
  - The asset can be positioned, rotated and scaled by setting the translate, rotate and scale attributes on the root prim. *A grid is visible. Asset is translated to 10 units in x via the xformCommonApi. The asset and the stage origin are framed by the camera. Asset is translated to 10 units in y via the xformCommonApi. The asset and the stage origin are framed by the camera. Asset is translated to 10 units in z via the xformCommonApi. The asset and the stage origin are framed by the camera.*
* - Transformation and Pivot Point
  - VG.025
  - The transformation gizmo (manipulator) for the asset's root prim appears at the logical pivot point as defined in the specification (e.g., at the center of the base for an object that sits on the ground). *A "Pivot gizmo" prim is positioned at the computed transform of the assets root prim.*
* - Transformation and Pivot Point
  - VG.025
  - An asset designed to articulate (e.g., a hinged door) rotates correctly around the specified pivot point of the moving part. *Asset rotates in 10 degree steps in x via the xformCommonApi. The asset and the stage origin are framed by the camera.*
* - Geometry and Shading
  - VG.MESH.001, VG.014
  - The asset's surfaces render correctly without unintended holes or gaps. *Light spins around the object*
* - Geometry and Shading
  - VG.028
  - With back-face culling enabled in the viewport, surfaces are not culled incorrectly, verifying proper normal orientation. *Camera spins around the object*
* - Geometry and Shading
  - VG.027, VG.028, VG.029
  - Surface shading appears smooth (no faceting) for curved surfaces and shows hard edges where intended, verifying that normals are authored correctly. *Camera spins around the object*
* - Composition and Metadata
  - HI.004
  - The asset can be successfully referenced into a parent aggregation scene without the need to specify the prim path (default prim).
```


## Python Testing Script

We supply a simple [test script](../_static/minimal_placeable_visual/test-minimal_placeable_visual.py) to run most of the tests so you can verify the feature in your own runtime with your own assets. A test asset is available for download [here](../_static/minimal_placeable_visual/toolbox.usdc), as well as the resulting USD stage [here](../_static/minimal_placeable_visual/minimal_placeable_visual-runtime_test-toolbox.zip). Note that selection and hierarchy tests are not included in the test script.

```bash
# Example
pip install usd-core
python test-minimal_placeable_visual.py toolbox.usdc minimal_placeable_visual-runtime_test-toolbox
```


```{literalinclude} ../_static/minimal_placeable_visual/test-minimal_placeable_visual.py
:language: python
:linenos:
:caption: test-minimal_placeable_visual.py
```
