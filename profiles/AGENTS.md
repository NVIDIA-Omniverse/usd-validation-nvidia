<!-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved. -->
<!-- SPDX-License-Identifier: Apache-2.0 AND CC-BY-4.0 -->

# AGENTS.md - AI Agent Guide for usd-profiles-nvidia

> **Note:** This package now lives in the `usd-validation-nvidia` repository as the `profiles/`
> workspace member (migrated under OMPE-100593). Paths and commands in this file are relative to
> the `profiles/` directory; run repo tooling (`./repo.sh format`, `./repo.sh lint ruff`) from the
> repository root. To run the test suite from the repository root:
> `uv run --no-project --with ./profiles --with "sphinx>=7.2.6" --with "myst-parser>=4.0.0" python -m unittest discover -s profiles/tests`

This file gives AI coding agents the minimum context needed to work effectively on this package. Use it as a
starting map together with the repository root `AGENTS.md`.

## What This Repo Is

`usd-profiles-nvidia` is a Python package for defining OpenUSD profile specifications and generating Python code
from them. It provides:

  * Markdown parsers for requirements, capabilities, features, and profiles (`src/usd_profiles_nvidia/markdown/`)
  * TOML profile parsing support (`src/usd_profiles_nvidia/toml/`)
  * Python enum/dataclass code generation (`src/usd_profiles_nvidia/codegen/`)
  * Optional Sphinx extensions for rendering profile documentation (`src/usd_profiles_nvidia/sphinx/`)

Primary use case: author structured profile specs, then generate importable Python enums for downstream tools.

## Start Here

  * Read `README.md` for package context, installation, and top-level examples.
  * Use `examples/python/minimal/` as the runnable minimal codegen reference.
  * The standalone repo's `.agents/skills/` guides were not migrated; repository-level agent skills
    live in the root `.agents/skills/`.

## Repo Layout (High-Level)

  * `src/usd_profiles_nvidia/` - Current Python package source
  * `src/omni/usd_profiles/` - Compatibility import package
  * `tests/` - Unit tests and parser/codegen fixtures
  * `tests/resources/` - Minimal and edge-case spec fixtures
  * `examples/python/minimal/` - Minimal runnable codegen example
  * `docs/` - Documentation support files

## Common Workflows

### Code Generation (uv)

  * Generate the minimal example:
    ```bash
    uv run \
      --no-project \
      --with . \
      python -m usd_profiles_nvidia.codegen \
        --docs-root examples/python/minimal/specs \
        --destination-dir _build/minimal \
        --package-name example_profiles
    ```
  * Generated files appear under `_build/minimal/example_profiles`.

### Tests

  * Tests live under `tests/`.
  * If working on parser or codegen behavior, run targeted tests first, then broader suites as needed.

## Use Skills for Task-Specific Work

Repository-level agent skills live in the root `.agents/skills/`. If you add a repeated
usd-profiles-nvidia workflow, add a matching skill there and reference a runnable example
(for instance `profiles/examples/python/minimal/`) where practical.

## Agent Expectations

  * Prefer small, targeted edits over broad refactors unless requested.
  * Keep examples, skills, and CLI option names in sync with code behavior.
  * Keep runnable examples under `examples/` and have skills point to those files.
  * Use `--package-name` for codegen examples; the older namespace option is deprecated.
  * Mention `usd-profiles-nvidia[sphinx]` only for optional Sphinx documentation integration, not as a codegen
    requirement.
  * Preserve licensing headers and proprietary notices where present.
  * Do not commit generated `_build/`, local virtual environments, or package caches.
  * Keep profile codegen guidance focused on usd-profiles-nvidia. Runtime validation integration belongs in
    downstream documentation.

## Notes

  * `profiles.toml` is authoritative when present in a profiles directory; use `profiles.toml.example` for
    documentation-only examples that should not affect Markdown profile parsing.
  * The package includes compatibility imports under `omni.usd_profiles`; prefer `usd_profiles_nvidia` for new examples.
  * Sphinx support is optional and separate from the core codegen flow.
