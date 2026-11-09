@AGENTS.md

# Claude Code — project notes

Claude-specific additions beyond `AGENTS.md`. Shared instructions live in the
root `AGENTS.md` file above.

## Subagents & skills

Canonical location: `.agents/agents/` and `.agents/skills/` — **edit there only**.
`.claude/agents/`, `.claude/skills/`, `.cursor/agents/`, `.cursor/skills/` are
symlinks for tool discovery; never edit through the symlinks.

Agent memory lives under `.claude/agent-memory/<agent-name>/` (one dir per
installed agent). These are writable by Claude Code.

Portable pattern docs live in `.agents/docs/` (always bundled). Project-specific
docs under `docs/` supplement and override when present.

## Local overrides

Personal Claude-only instructions: `CLAUDE.local.md` (gitignored).
