# Naming Paths Feature

| **Property**            | **Value**   |
|-------------------------|-------------|
| Version                 | 1.0.0       |
| Dependency              | OpenUSD     |

## Description

Feature that declares requirements via a nested bullet list (Capability → Requirements → requirement link).

## Requirements

* Capability: [Core/Naming_Paths](capabilities/naming_paths/capability-naming_paths.md)
    * Requirements
        * [Prim-Naming-Convention](capabilities/naming_paths/requirements/prim-naming-convention.md)
            * NP.001 | version 0.1.0
            * [Rule | Implementation](capabilities/naming_paths/validation.py)
