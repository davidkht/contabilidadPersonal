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

Control de deudas personales: API FastAPI + SQLite (JWT, roles admin/usuario) y frontend estático
en `web/` (ES modules, sin build). Ver `README.md`. `legacy/` es un respaldo de la app de escritorio:
no editar.

### Commands

```bash
uv sync                 # dependencias
./app.sh dev            # API + web con recarga (http://localhost:8000, docs en /api/docs)
./app.sh                # Docker en primer plano (Ctrl+C apaga todo)
uv run pytest           # tests
uv run ruff check src tests
```

### Layout

`src/api` (HTTP, rutas finas) → `src/services` (casos de uso + DTOs) → `src/ports` (Protocol) ←
`src/db` (SQLite). Composition root: `src/core/dependencies.py`. Las rutas no importan `src.models`
ni `src.db`.
