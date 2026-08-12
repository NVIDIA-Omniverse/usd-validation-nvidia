# invalid-enum-default

| Code          | VG.RTX.999           |
|---------------|----------------------|
| Version       | 1.0.0                |
| Validator     |                      |
| Compatibility | {compatibility}`RTX` |
| Tags          | {tag}`test`          |

## Summary

Test requirement with invalid enum default (should fail validation).

## Parameters

| Parameter | Type                 | Default Value |
|-----------|----------------------|---------------|
| MODE      | enum("A", "B", "C")  | D             |

## Description

This requirement has an invalid default value that is not in the enum values.

