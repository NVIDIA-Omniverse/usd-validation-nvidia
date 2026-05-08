---
name: extending-validation
description: Extend NVIDIA USD Validation with custom rules, requirements, features, profiles, and Python entry-point plugins. Use when adding validator packages, registering custom rules, debugging missing entry points, or integrating additional validation semantics.
---

# Extending NVIDIA USD Validation

## Overview

Use this skill when creating a package that adds validation behavior to `usd-validation-nvidia`. Extensions are discovered through Python entry points and must register their rules, requirements, features, or profiles during plugin startup.

## Plugin Package Shape

Declare a package entry point in `pyproject.toml`:

```toml
[project]
name = "my-usd-validation-plugin"
version = "0.1.0"
dependencies = ["usd-validation-nvidia[usd]"]

[project.entry-points."usd_validation_nvidia"]
my_plugin = "my_validator.plugin:plugin"
```

The legacy `omni.asset_validator` entry-point group is also discovered for compatibility, but new packages should prefer `usd_validation_nvidia`.

## Minimal Rule Plugin

```python
from dataclasses import dataclass

from pxr import UsdGeom

from usd_validation_nvidia import (
    BaseRuleChecker,
    register_requirements,
    register_rule,
    unregister_requirements,
    unregister_rule,
)


@dataclass(frozen=True)
class CustomRequirement:
    code: str
    version: str
    message: str
    display_name: str | None = None
    path: str | None = None
    tags: tuple[str, ...] = ()
    parameters: tuple = ()
    examples: tuple = ()


MESH_EXTENT_REQUIRED = CustomRequirement(
    code="CUSTOM_MESH_001",
    version="1.0.0",
    display_name="Mesh extent is authored",
    message="Meshes must author extent for deterministic bounds.",
)


class MeshExtentChecker(BaseRuleChecker):
    """Require each UsdGeomMesh to author extent."""

    def CheckPrim(self, prim):
        if prim.IsA(UsdGeom.Mesh) and not prim.GetAttribute("extent").HasAuthoredValue():
            self._AddFailedCheck(
                requirement=MESH_EXTENT_REQUIRED,
                at=prim,
            )


class Plugin:
    def on_startup(self) -> None:
        register_requirements(MESH_EXTENT_REQUIRED)(MeshExtentChecker)
        register_rule("Custom")(MeshExtentChecker)

    def on_shutdown(self) -> None:
        unregister_rule(MeshExtentChecker)
        unregister_requirements(MeshExtentChecker)


plugin = Plugin()
```

## Rule Callback Surface

Subclass `BaseRuleChecker` and override the narrowest callback needed:

- `CheckStage(stage)` for whole-stage metadata or cross-stage checks.
- `CheckPrim(prim)` for prim-local validation.
- `CheckLayer(layer)` for Sdf layer checks.
- `CheckDependencies(stage, layerDeps, assetDeps)` for dependency validation.
- `CheckUnresolvedPaths(unresolvedPaths)` for unresolved asset-path reporting.
- `CheckDiagnostics(diagnostics)` for USD diagnostics collected while opening the stage.
- `CheckZipFile(zipFile, packagePath)` for package validation.

Report issues with `_AddFailedCheck`, `_AddWarning`, `_AddError`, or `_AddInfo`. Use `requirement=...` when the issue implements a requirement so JSON output can map failures back to profile and feature status.

## Verify Registration

Install the plugin in the same Python environment as the engine, then run:

```bash
nvidia_usd_validate --help
```

Confirm that the category, rule, or requirement appears. Then test narrowly:

```bash
nvidia_usd_validate --category Custom asset.usd
nvidia_usd_validate --rule MeshExtentChecker asset.usd
nvidia_usd_validate --requirement CUSTOM_MESH_001 asset.usd
```

## Common Pitfalls

- The plugin package is installed in a different environment from `usd-validation-nvidia`.
- The entry-point group or import path in `pyproject.toml` is misspelled.
- `on_startup()` imports USD plugins or resources too eagerly, creating noisy runtime diagnostics before validation starts.
- A rule reports a message but not `requirement=...`, so profile JSON cannot connect the issue to a requirement.
- `on_shutdown()` does not unregister rules, which can pollute long-lived processes or tests.
