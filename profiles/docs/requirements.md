# Requirements

A requirement is one atomic, testable statement about an asset. It describes what must be true, why it matters, and
which validator can report pass or failure for that rule.

For the factory profile, the custom requirement is: every boundable prim must fit inside the configured bounding-box
dimensions.

## Required Sections

Every requirement Markdown file has:

- a level-1 title
- a metadata table with `Code`, `Version`, `Compatibility`, `Validator`, and `Tags`
- a `Summary` section

The `Code` is local to the authoring package until code generation qualifies it with `--reverse-domain`.

## Metadata

```markdown
| Code          | GEOMETRY.001             |
|---------------|--------------------------|
| Version       | 1.0.0                    |
| Compatibility | {compatibility}`OpenUSD` |
| Validator     | FactoryBoundsChecker     |
| Tags          | {tag}`correctness`       |
```

Use `Validator` as documentation metadata for the rule that enforces the requirement. Generated Python requirement
objects are bound to rules by the validation plugin with `register_requirements(...)`.

## Parameters

Requirement parameters define values that validation rules can read through `self.parameters`. They are the right place
for factory-specific bounding-box limits because different production lines can use different dimensions without
changing the rule code.

```markdown
## Parameters

| Parameter    | Type  | Default Value |
|--------------|-------|---------------|
| MAX_X_METERS | float | 6.0           |
| MAX_Y_METERS | float | 6.0           |
| MAX_Z_METERS | float | 4.0           |
```

Supported parameter types are `int`, `bool`, `float`, and `enum("A", "B", "C")`. Default values are parsed into the
generated package and can be overridden at runtime.

## Optional Sections

Use optional sections to make the requirement actionable:

- `Description` explains the validation criteria.
- `Why is it required?` records the operational reason for the requirement.
- `Examples` shows valid and invalid asset snippets.
- `How to comply` gives asset authors direct remediation steps.
- `For More Information` links to external references.

## Complete Example

```{eval-rst}
.. literalinclude:: ../examples/factory-bounds/specs/capabilities/factory_geometry/requirements/factory-boundable-size.md
   :language: md
```
