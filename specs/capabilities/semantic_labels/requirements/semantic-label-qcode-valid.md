# semantic-label-qcode-valid

| Code          | SL.QCODE.001                              |
|---------------|--------------------------------------------|
| Version       | 1.0.0                                      |
| Validator     | {oav-validator-latest-link}`sl-qcode-001` |
| Compatibility | {compatibility}`nvidia-omniverse`        |
| Tags          | {tag}`correctness`                        |

## Summary

If the Wikidata ontology is used, Q-Codes must be valid, properly formatted, and retrievable from wikidata.org.

## Description

Q-Codes used for semantic labels must exist in the Wikidata database and represent appropriate concepts for the labeled objects.
The `labels:wikidata_qcode` attribute must be used to store the Q-Code for the semantic label at the `default` time.
Qcodes must start with a `Q` followed by one or more digits (`[0-9]`)

## Why is it required?

- NVIDIA uses the QCode taxonomy for many assets in Omniverse asset libraries
- Assets intended to be used alongside NVIDIA Omniverse assets should use the same ontology


## Examples

### Invalid: Non-existent Q-Code

```usd
#usda 1.0

def Xform "Vehicle" (
    prepend apiSchemas = ["SemanticsLabelsAPI:wikidata_qcode"]
)
{
    token[] semantics:labels:wikidata_qcode = ["Q999999999"]  # Q-Code doesn't exist
}
```

### Invalid: Q-Code for wrong concept type

```usd
#usda 1.0

def Xform "Car" (
    prepend apiSchemas = ["SemanticsLabelsAPI:wikidata_qcode"]
)
{
    token[] semantics:labels:wikidata_qcode = ["Q5"]  # Q-Code for "human", not vehicle
}
```

### Invalid: Incorrect Q-Code format

```usd
#usda 1.0

def Xform "BadLabel" (
    prepend apiSchemas = ["SemanticsLabelsAPI:wikidata_qcode"]
)
{
    token[] semantics:labels:wikidata_qcode = ["Car"]  # Not a Q-Code
}
```

### Invalid: Empty array

```usd
#usda 1.0

def Xform "NoLabel" (
    prepend apiSchemas = ["SemanticsLabelsAPI:wikidata_qcode"]
)
{
    token[] semantics:labels:wikidata_qcode = []  # Must have at least one value
}
```

### Valid: Existing and appropriate Q-Code

```usd
#usda 1.0

def Xform "Vehicle" (
    prepend apiSchemas = ["SemanticsLabelsAPI:wikidata_qcode"]
)
{
    token[] semantics:labels:wikidata_qcode = ["Q42889"]  # Valid Q-Code for "car"
}
```

## How to comply
- Use valid Wikidata Q-Codes that follow the proper format (Q + digits)
- Verify Q-Codes exist on wikidata.org
- Use appropriate Q-Codes for object types
- Check Q-Code validity during asset creation

## For More Information
- [Wikidata](https://www.wikidata.org)
- [Wikidata Q-Code Search](https://www.wikidata.org/wiki/Special:ItemByTitle)
- [Wikidata Q-Code Format](https://www.wikidata.org/wiki/Help:Items)