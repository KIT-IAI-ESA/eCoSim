# .agents

Tool-agnostic configuration for AI coding agents. Everything here is plain Markdown with
YAML frontmatter — no vendor-specific syntax — so the same instructions serve every tool.

```
.agents/
  guidelines/   always-applicable rules (communication, coding, repository facts)
  skills/       procedures for recurring tasks, one directory per skill
  commands/     explicit user-invoked commands
  roles/        agent personas, referenced by tool configuration
```

## How the tools attach

| Tool | Hook | Mechanism |
|---|---|---|
| Any `AGENTS.md`-aware tool (opencode, Codex, Cursor, Copilot, …) | `AGENTS.md` | read automatically from the repository root |
| Claude Code | `CLAUDE.md`, `.claude/skills`, `.claude/commands` | symlinks into this directory |
| JetBrains Junie | `.junie/guidelines.md` | pointer file |
| opencode (containerised, `ai/opencode/`) | `opencode.*.json` | `agent.ecosim-programmer.prompt` → `roles/ecosim-programmer.md` |

The symlinks are checked in, so a fresh clone needs no setup:

```shell
ls -l CLAUDE.md .claude/skills .claude/commands
```

## Adding a skill

A skill is a directory with a `SKILL.md`:

```markdown
---
name: my-skill
description: What it does, and when an agent should reach for it.
---

# My skill
…
```

The directory name must equal `name` (lowercase, hyphens). The `description` is what an
agent sees when deciding whether the skill is relevant, so write it as a trigger — say when
to use it, not just what it is.

Write down what is **not** obvious from reading the repository: the command that does not
work from the root, the flag that must be set, the pitfall that already cost someone an
afternoon. A skill that restates what `--help` says earns nothing.

## Adding a guideline

Guidelines apply always, so keep them short — they are prepended to every conversation.
Anything task-specific belongs in a skill instead.
