# semantic-label-schema

| Code          | SL.003                              |
|---------------|-------------------------------------|
| Version       | 1.0.0                              |
| Validator      | {oav-validator-latest-link}`sl-001` |
| Compatibility | {compatibility}`open-usd`          |
| Tags          | {tag}`correctness`                 |

## Summary

Semantic labels must use the SemanticsLabelsAPI schema

## Description

The SemanticsLabelsAPI schema must be applied correctly.

## Why is it required?

- Correct usage of the SemanticsLabelsAPI ensures compatibility with open standards
- Previous, proprietary implementations of semantic labeling have been used in NVIDIA Omniverse. But they are not compatible with the open standard.

## Examples

### Invalid: Wrong schema name

```usd
#usda 1.0

def Xform "Vehicle" (
    prepend apiSchemas = ["SemanticsAPI:wikidata_qcode"]  # Incorrect schema
)
{
    token[] semantics:labels:wikidata_qcode = ["Q42889"]
}
```

### Invalid: Missing schema

```usd
#usda 1.0

def Xform "Car" {
    # Direct attribute without schema - not valid
    token[] semantics:labels:wikidata_qcode = ["Q42889"]
}
```

### Valid: Correct schema usage

```usd
#usda 1.0

def Xform "Truck" (
    prepend apiSchemas = ["SemanticsLabelsAPI:wikidata_qcode"]
)
{
    token[] semantics:labels:wikidata_qcode = ["Q42889"]
}
```

### Invalid: No API instance name (taxonomy)

```usd
#usda 1.0

def Xform "Tree" (
    prepend apiSchemas = ["SemanticsLabelsAPI"]
)
{
    token[] semantics:labels = ["Q42889"]
}
```

## How to comply
- Apply correct SemanticsLabelsAPI schema
- Use proper attribute name
- Ensure schema is prepended to prim

## For More Information
- [USD API Schemas Documentation](https://openusd.org/release/api/usd_api_schemas_page_front.html)