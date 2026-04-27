# Dense Captions

## Overview

This capability provides requirements for the detailed, human-readable descriptions of 3D assets and comprised sub-hierarchies. These detailed captions may be used to support AI training and scene understanding.

## Granularity

At a mininum, the **root prim** of the asset should contain documentation metadata, holding a Dense Caption string.
Prims representing sub-objects or parts within the asset may additionally add dense captions.

## Schema

Dense captions currently do not use a schema and they are conventional.

NVIDIA convention is to use the OpenUSD documentation (doc) string as shown below.

## USDA Sample

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

## Requirements

<!-- DENSE_CAPTIONS_REQUIREMENTS_LIST_START -->

```{requirements-table}
```

<!-- DENSE_CAPTIONS_REQUIREMENTS_LIST_END -->
