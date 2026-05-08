---
name: profile-codegen
description: Generating Python profile packages with usd-profiles-nvidia. Use when authoring profile, feature, capability, or requirement specs, running usd_profiles_nvidia.codegen, generating importable profile enums, or preparing profile data for validation plugins.
---

# Profile Codegen

## Overview

Use `usd-profiles-nvidia` to author profile specifications and generate Python modules containing `Requirements`, `Capabilities`, `Features`, and `Profiles` enums. The generated package can then be used by validation plugins or tooling that registers profiles into `usd-validation-nvidia`.

Install the profile framework where code generation runs:

```bash
python -m pip install usd-profiles-nvidia
```

> **Source:** `C:\sources\usd-profiles-nvidia\README.md`
>
> **Source:** `C:\sources\usd-profiles-nvidia\src\usd_profiles_nvidia\codegen\_cli.py` defines the current CLI flags.

## Spec Layout

Use a docs/spec tree with capabilities, features, and profiles:

```text
specs/
  capabilities/
    geometry.md
    requirements/
      mesh-valid.md
  features/
    minimal-placeable-visual.md
  profiles/
    profile-prop-robotics-neutral.md
```

Some projects may use `profiles/profiles.toml` for multi-version profile definitions. The TOML table name is preserved as the profile ID, so `Prop-Robotics-Neutral` remains case-sensitive in downstream CLI usage.

## Requirement Spec

Example `specs/capabilities/requirements/single-root.md`:

```markdown
# single-root

| Code          | REQ.001                 |
|---------------|-------------------------|
| Version       | 1.0.0                   |
| Compatibility | {compatibility}`OpenUSD` |
| Validator     |                         |
| Tags          | {tag}`essential`        |

## Summary

USD stage must have a single root prim.

## Description

Every USD asset must contain one root prim from which all other prims descend.
```

The generated enum member includes the code and version, for example `Requirements.REQ_001_V1_0_0`.

## Capability Spec

Example `specs/capabilities/geometry.md`:

````markdown
# Geometry

## Overview

Geometry readiness requirements.

## Requirements

```{requirements-table}
```
````

The requirements table is populated from requirement specs under the capability's `requirements/` folder.

## Feature Spec

Example `specs/features/minimal-placeable-visual.md`:

````markdown
# Minimal Placeable Visual

| Property   | Value   |
|------------|---------|
| Version    | 1.0.0   |
| Dependency | OpenUSD |

## Description

Minimal visual asset feature.

## Requirements

```{features-table}
REQ.001@1.0.0
```
````

## Profile Spec

Markdown profile example:

```markdown
# Prop Robotics Neutral

Minimal prop robotics profile.

## Features

- [Minimal Placeable Visual](../features/minimal-placeable-visual.md)
```

TOML profile example:

```toml
[Prop-Robotics-Neutral]
"1.0.0" = {features = [
    {"FET001_BASE_NEUTRAL" = {version = "0.1.0"}},
    {"FET003_BASE_NEUTRAL" = {version = "0.1.0"}},
]}
```

Use TOML when one profile ID needs multiple versions.

## Generate Python

Run code generation with current flags:

```bash
python -m usd_profiles_nvidia.codegen --docs-root specs --destination-dir generated --package-name mypackage.profiles
```

Generated files appear under:

```text
generated/
  mypackage/
    profiles/
      __init__.py
      _protocols.py
      _requirements.py
      _capabilities.py
      _features.py
      _profiles.py
```

For reverse-domain identifiers:

```bash
python -m usd_profiles_nvidia.codegen --docs-root specs --destination-dir generated --package-name simready.foundations.core --reverse-domain com.nvidia.simready
```

`--namespace` exists for compatibility but is deprecated. Use `--package-name` and `--reverse-domain` in new guidance.

## Use Generated Profiles with Validation

Generated profile enums are data. A validation plugin still needs to register them with the validation engine:

```python
import mypackage.profiles as profiles
from usd_validation_nvidia import register_profiles, unregister_profiles


class Plugin:
    def on_startup(self):
        register_profiles(profiles.Profiles)

    def on_shutdown(self):
        unregister_profiles(profiles.Profiles)


plugin = Plugin()
```

Rules should register the generated requirements they implement:

```python
import mypackage.profiles as profiles
from usd_validation_nvidia import BaseRuleChecker, register_requirements


@register_requirements(profiles.Requirements.REQ_001_V1_0_0)
class SingleRootChecker(BaseRuleChecker):
    def CheckStage(self, stage):
        roots = [p for p in stage.GetPseudoRoot().GetChildren() if p.IsValid()]
        if len(roots) != 1:
            self._AddFailedCheck(
                message="Stage must have exactly one root prim.",
                requirement=profiles.Requirements.REQ_001_V1_0_0,
            )
```

## Common Pitfalls

- Using the deprecated `--namespace` flag in new docs instead of `--package-name`.
- Assuming `usd-profiles-nvidia` automatically registers profiles with `nvidia_usd_validate`; generated profile data still needs a validation plugin entry point.
- Changing profile IDs or case and then expecting old CLI `--profile` values to work.
- Generating code into a directory that is not packaged or installed into the validation environment.
- Registering a profile whose requirements have no corresponding rule implementations.
