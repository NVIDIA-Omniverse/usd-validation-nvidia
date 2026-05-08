# USD Validation NVIDIA Skills Directory

This directory contains structured skill files for AI coding agents working with NVIDIA USD Validation. Each skill is a self-contained reference for a specific validation task.

## Structure

Each subdirectory contains a single `SKILLS.md` file with YAML frontmatter:

```text
skills/
  running-validation/SKILLS.md
  extending-validation/SKILLS.md
```

## SKILLS.md Format

```markdown
---
name: skill-name
description: What this skill covers. Use when user asks to ...
---

# Skill Title

## Overview
Brief explanation of when and why to use this.

## Workflow
Step-by-step instructions and commands.

## Key Concepts
Short reference for the relevant API or CLI surface.

## Common Pitfalls
Gotchas and things to verify.
```

## Available Skills

- `running-validation` - Install the validation stack, run `nvidia_usd_validate`, validate against profiles such as `Prop-Robotics-Neutral`, interpret JSON output, fix common failures, and integrate validation into CI.
- `extending-validation` - Create custom rule packages and entry-point plugins that register rules, requirements, features, or profiles.

## Updating Skills

When package names, CLI flags, output schema, profile behavior, or plugin APIs change, update the affected `SKILLS.md` file in the same change.
