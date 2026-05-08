# USD Validation NVIDIA Skills Directory

This directory contains structured skill files for AI coding agents working with NVIDIA USD Validation. Each skill is a focused, self-contained task guide with enough commands, file shapes, and troubleshooting detail for an agent to act without guessing.

## Structure

Each subdirectory contains a single `SKILLS.md` file with YAML frontmatter:

```text
skills/
  project-setup-python/SKILLS.md
  validate-asset/SKILLS.md
  reading-json-output/SKILLS.md
  fixing-validation-failures/SKILLS.md
  ci-validation/SKILLS.md
  profile-codegen/SKILLS.md
  extending-validation/SKILLS.md
```

## Available Skills

- `project-setup-python` - Create an isolated Python project, install the validation engine and profile tooling/package, author a tiny USDA sample, and run the first profile validation.
- `validate-asset` - Discover installed profiles/features/capabilities/requirements/rules and run scoped CLI validation with `nvidia_usd_validate`.
- `reading-json-output` - Read `--json-output`, understand the profile/feature/requirement tree, and map rule issues back to compliance failures.
- `fixing-validation-failures` - Triage common validation failures and decide when to use automatic fixes versus manual USD edits.
- `ci-validation` - Add profile validation to CI, preserve JSON/CSV artifacts, and keep validation deterministic.
- `profile-codegen` - Author profile/capability/feature/requirement specs and generate Python profile enums with `usd-profiles-nvidia`.
- `extending-validation` - Create custom rule/profile packages and Python entry-point plugins.

## SKILLS.md Format

```markdown
---
name: skill-name
description: What this skill covers. Use when user asks to [trigger phrases].
---

# Skill Title

## Overview
Brief explanation of when and why to use this.

## Workflow
Step-by-step commands and files.

## Key Types / Commands
Quick reference of the API or CLI surface involved.

## Common Pitfalls
Gotchas and things to watch out for.
```

## Writing Guidance

- Keep each skill narrow enough that an agent can choose it from the frontmatter description.
- Prefer concrete commands, file layouts, and small examples over broad prose.
- Keep package names exact: `usd-validation-nvidia` for this validation package and `usd-profiles-nvidia` for the profile framework/codegen package.
- Treat profile IDs, feature IDs, capability IDs, requirement codes, categories, and rule names as environment-specific. Tell agents to confirm them with `nvidia_usd_validate --help`.
- When API examples duplicate behavior that already has test coverage, point agents to the relevant test file as a source reference.

## Updating Skills

When package names, CLI flags, output schema, profile behavior, JSON/CSV fields, or plugin APIs change, update the affected `SKILLS.md` file in the same change.
