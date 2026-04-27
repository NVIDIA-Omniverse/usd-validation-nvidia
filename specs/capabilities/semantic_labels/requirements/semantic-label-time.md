# semantic-label-time

| Code          | SL.NV.002                              |
|---------------|----------------------------------------|
| Version       | 1.0.0                                  |
| Validator     | {oav-validator-latest-link}`sl-nv-001` |
| Compatibility | {compatibility}`rtx`                   |
| Tags          | {tag}`limitation`                      |

## Summary

Semantic label attributes must not contain time samples

## Description

This is a limitation of NVIDIA Sensor RTX - Semantic label attributes should be constant over time.

## Why is it required?

- NVIDIA Sensor RTX does not support time samples on semantic label attributes

## Examples

### Invalid: Time-sampled semantic labels

```usd
#usda 1.0

def Xform "Vehicle" (
    prepend apiSchemas = ["SemanticsLabelsAPI:wikidata_qcode"]
)
{
    token[] semantics:labels:wikidata_qcode.timeSamples = {
        0: ["Q42889"],  # car
        48: ["Q7813"]   # truck
    }
}
```

### Valid: Constant semantic labels

```usd
#usda 1.0

def Xform "Vehicle" (
    prepend apiSchemas = ["SemanticsLabelsAPI:wikidata_qcode"]
)
{
    token[] semantics:labels:wikidata_qcode = ["Q42889"]
}
```

## How to comply
- Remove time samples from semantic labels
- Use constant values for labels

## For More Information
- [USD Time Samples Documentation](https://openusd.org/release/api/usd_page_front.html#Usd_TimeSamples)