# Units

## Overview

This capability enables proper scaling and composition of assets with different unit systems, accurate physics simulation through consistent mass and scale units, correct time-sampled animation playback via standardized time units, and reliable color reproduction through defined colorspace units. These requirements ensure that assets have consistent and well-defined units for proper scaling when composed together as well as interpretation in simulation and rendering environments.

## Summary

- **An Asset must specify its units (e.g. linear units, mass units, time units, colorspaces)**
- **Additional requirements may be used to specify units for specific assets**
- **When composing assets with different units, corrective transformations need to be applied**

## Granularity

Every USD asset **must** have its scale (for most Omniverse related use cases, meters are recommended), mass (usually kilograms per unit) and time sampled mapping encoded within it. This information is vital to the successful composition of multiple USD files that are built at different scales.

For more detailed information on Units, please see the [**Units in USD**](https://docs.omniverse.nvidia.com/usd/latest/learn-openusd/independent/units.html) section of the Omniverse documentation.

## Schema

- [Encoding Stage Linear Units](https://openusd.org/dev/api/group___usd_geom_linear_units__group.html)
- [USD Physics Metrics](https://openusd.org/dev/api/usd_physics_2metrics_8h.html#details)
- [USD Timecode](https://openusd.org/dev/api/class_usd_time_code.html)

## USDA Sample

```python
#usda 1.0
(
    metersPerUnit = 1
    upAxis = "Z"
    kilogramsPerUnit = 1
    startTimeCode = 0
    endTimeCode = 100
    timeCodesPerSecond = 24
)

```

## Requirements
<!-- UNITS_REQUIREMENTS_LIST_START -->

```{requirements-table}
```

<!-- UNITS_REQUIREMENTS_LIST_END -->
