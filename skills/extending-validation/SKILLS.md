---
name: extending-validation
description: Extending NVIDIA USD Validation with custom rule and profile packages. Use when creating validator plugins, registering custom rules, requirements, features, capabilities, profiles, debugging missing Python entry points, or packaging additional validation semantics.
---

# Extending NVIDIA USD Validation

## Overview

Use this skill when creating a package that adds validation behavior to `usd-validation-nvidia`. Extensions are discovered through Python entry points and register rules, requirements, features, capabilities, or profiles during plugin startup.

For normal validation usage, use `skills/validate-asset/SKILLS.md`. For JSON interpretation, use `skills/reading-json-output/SKILLS.md`.

## Plugin Package Shape

Recommended package layout:

```text
my-usd-validation-plugin/
  pyproject.toml
  src/
    my_validator/
      __init__.py
      plugin.py
```

Declare a package entry point in `pyproject.toml`. New plugins should use the `usd_validation_nvidia` group:

```toml
[project]
name = "my-usd-validation-plugin"
version = "0.1.0"
dependencies = ["usd-validation-nvidia[usd]"]

[project.entry-points."usd_validation_nvidia"]
my_plugin = "my_validator.plugin:plugin"
```

The legacy `omni.asset_validator` entry-point group is also discovered for compatibility, but new packages should prefer `usd_validation_nvidia`.

> **Source:** `src/usd_validation_nvidia/_plugins.py` defines entry-point discovery.
>
> **Source:** `tests/test_plugins.py` covers the default plugin and external entry-point behavior.

## Minimal Requirement-Backed Rule

Create `src/my_validator/plugin.py`:

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
    display_name: str | None = None
    message: str | None = None
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
                message="Mesh must author extent.",
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

Why `requirement=...` matters: profile and feature JSON can only connect an issue to a compliance requirement when the issue includes a requirement.

## Rule Callback Surface

Subclass `BaseRuleChecker` and override the narrowest callback needed:

- `CheckStage(stage)` for whole-stage metadata or cross-stage checks.
- `CheckPrim(prim)` for prim-local validation.
- `CheckLayer(layer)` for Sdf layer checks.
- `CheckDependencies(stage, layerDeps, assetDeps)` for dependency validation.
- `CheckUnresolvedPaths(unresolvedPaths)` for unresolved asset-path reporting.
- `CheckDiagnostics(diagnostics)` for USD diagnostics collected while opening the stage.
- `CheckZipFile(zipFile, packagePath)` for package validation.
- `CheckFormatDependency(dependency)` for dependencies returned by registered asset formats.

Report issues with `_AddFailedCheck`, `_AddWarning`, `_AddError`, or `_AddInfo`. Use `requirement=...` when the issue implements a requirement so JSON output can map failures back to profile and feature status.

> **Source:** `src/usd_validation_nvidia/_base_rule_checker.py` defines rule callbacks and issue helpers.

## Register Features, Capabilities, or Profiles

Requirement-backed rules are enough when an existing profile package already references the requirement. If the plugin also defines new validation scopes, register them from `on_startup()`.

The protocols are lightweight objects with the required fields:

```python
from dataclasses import dataclass

from usd_validation_nvidia import register_capability, register_profile


@dataclass(frozen=True)
class CustomCapability:
    id: str
    version: str
    path: str
    requirements: list


@dataclass(frozen=True)
class CustomProfile:
    id: str
    version: str
    path: str
    capabilities: list
```

Then register and unregister them alongside rules:

```python
CAPABILITY = CustomCapability(
    id="Custom-Mesh-Readiness",
    version="1.0.0",
    path="custom-mesh-readiness",
    requirements=[MESH_EXTENT_REQUIRED],
)
PROFILE = CustomProfile(
    id="Custom-Prop-Neutral",
    version="1.0.0",
    path="custom-prop-neutral",
    capabilities=[CAPABILITY],
)
```

Use the matching unregister functions in `on_shutdown()` for long-lived processes and tests.

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

If the plugin registers a profile, test the profile too:

```bash
nvidia_usd_validate --profile Custom-Prop-Neutral --json-output reports/custom-profile.json asset.usd
```

## Debug Missing Entry Points

Use this checklist when the package installs but validation scope does not appear in `--help`:

1. Confirm the plugin package and `usd-validation-nvidia` are installed in the same environment.
2. Confirm the entry-point group is `usd_validation_nvidia`.
3. Confirm the entry-point value imports and resolves to the plugin object.
4. Import the plugin module manually to expose import-time errors.
5. Run `nvidia_usd_validate --help` again after reinstalling the package.

## Common Pitfalls

- The plugin package is installed in a different environment from `usd-validation-nvidia`.
- The entry-point group or import path in `pyproject.toml` is misspelled.
- `on_startup()` imports USD plugins or resources too eagerly, creating noisy runtime diagnostics before validation starts.
- A rule reports a message but not `requirement=...`, so profile JSON cannot connect the issue to a requirement.
- `on_shutdown()` does not unregister rules, which can pollute long-lived processes or tests.
- A custom profile references a requirement that has no registered validator.
