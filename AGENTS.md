# AGENTS.md

Shared instructions for AI coding agents (Cursor, Claude Code, Codex, Copilot, etc.) working in this repository.

## Python tooling (all projects)

This workspace uses **uv** for Python package management. Follow these rules in
every Python repo unless a project-specific section below says otherwise.

### Do

- Run Python tools through **`uv run`**, never by activating a virtualenv.
- Install/sync dependencies with **`uv sync`** (or `uv sync --group dev`).
- Add/remove dependencies with **`uv add`** / **`uv remove`** so `pyproject.toml`
  and `uv.lock` stay in sync.
- Commit **`pyproject.toml`** and **`uv.lock`**; ignore **`.venv/`**.

### Do not

- Do not run `source .venv/bin/activate`, `deactivate`, or assume a manual venv.
- Do not run bare `pytest`, `ruff`, `mypy`, `cdk` when they are project
  dependencies — use `uv run <tool> ...`.
- Do not edit `uv.lock` by hand.

### Containers

Development runs in isolated containers (Cursor devcontainers, sbx microVMs).
Pre-approved shell permissions assume this environment. Prefer `uv run`.


---

## Project: contabilidadpersonal

### Overview

Add your description here

### Commands

```bash
# Setup
uv sync

# Tests
uv run pytest

# NOTE: legacy requirements*.txt present — migrate to pyproject + uv sync
```

### Layout

```
contabilidadpersonal/
  databases/
  docs/
  src/
  web/
```

### Stack

- Python 3.12

### AI harness

Skills are canonical under **`.agents/skills/`** (symlinked into `.claude/skills` and `.cursor/skills`). Subagents are real files in **`.cursor/agents/`** (Cursor-native) and **`.claude/agents/`** (Claude Code; also read by Cursor for compatibility).

- Subagents installed: backend-feature-architect, infra-architect, api-backend-architect, frontend-component-architect, frontend-state-architect
- Skills installed: uv-python, vite-react
- Portable pattern docs: `.agents/context/` (mode-filtered). Project `docs/` supplements when present.
- MCP: edit `.agents/mcp.servers.yaml`, then `dvh mcp`.

### Project docs

_Add product-specific docs under `docs/` as needed._
