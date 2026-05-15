# usd-validation-nvidia Skills Directory

This directory contains structured skill files for AI coding agents working on the usd-validation-nvidia codebase.
Each skill is a self-contained reference for a specific validation task, with code snippets from live examples and
tests where possible.

For agents that do not automatically discover `.agents/skills/`, such as Claude in some setups or Codex CLI when skills
are not auto-discovered, prompt the agent to read `AGENTS.md` and this `.agents/skills/README.md` first, then the
specific `.agents/skills/*/SKILL.md` file that matches the task.

## Structure

Each subdirectory contains a single `SKILL.md` file with YAML frontmatter:

```text
.agents/skills/
  project-setup-python/SKILL.md
  project-venv-setup/SKILL.md
  validate-requirements/SKILL.md
```

## SKILL.md Format

```markdown
---
name: skill-name
version: "1.0.0"
license: Apache-2.0
description: "What this skill covers. Use when user asks to [trigger phrases]."
metadata:
  author: NVIDIA
  tags:
    - example
---

<!-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved. -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Skill Title

## Overview
Brief explanation of when and why to use this.

## Python
Step-by-step with code snippets.

## Key Types / Functions
Quick reference of the API surface involved.

## Common Pitfalls
Gotchas and things to watch out for.
```

## Code Snippet References

Skills reference live code in test and example files instead of duplicating snippets inline. This keeps code in
skills accurate as the API evolves.

### Marker format in source files

```python
# [snippet:custom-rule]
class ExampleDefaultPrimChecker(BaseRuleChecker):
    ...
# [/snippet:custom-rule]
```

Names are kebab-case and unique within each file.

### Reference format in SKILL.md

Replace inline code blocks with a blockquote directive:

```markdown
> **Source:** `examples/python/minimal/main.py` snippet `custom-rule`
```

Agents read the referenced file between the `# [snippet:name]` and `# [/snippet:name]` markers to get the current code.
For very small config files, such as an example `pyproject.toml`, a skill may omit the snippet name and reference the
whole file.

## Adding a New Skill

1. Add or identify a focused test or example that demonstrates each code path the skill will reference.
2. Wrap every illustrative section in `# [snippet:name]` / `# [/snippet:name]` markers.
3. Create a new directory under `.agents/skills/` named after the skill, using kebab-case.
4. Add a `SKILL.md` file inside it following the format above.
5. Prefer `> **Source:** ...` blockquotes for API usage so skills stay aligned with executable examples.

## Updating Skills

When you make changes to package names, CLI flags, output schema, profile behavior, examples, or plugin APIs that
affect an existing skill, update the corresponding `SKILL.md` to keep it accurate.

## Modifying Tests or Examples

- Preserve snippet markers. If you move or restructure marked code, update the markers to stay around the illustrative
  section.
- Do not remove markers without also removing or updating every `> **Source:**` reference in `.agents/skills/`.
- Add markers to new tests or examples that demonstrate API workflows. If the workflow maps to an existing skill, add a
  reference there. If not, consider creating a new skill.
