---
name: uv-python
description: >-
  Run Python tooling via uv in this workspace. Use when installing dependencies,
  running pytest, ruff, mypy, uvicorn, cdk, scripts, or any Python CLI. Never
  activate virtualenvs — use uv sync and uv run instead.
---

# uv Python workflow

This project uses **uv** for Python package management. Follow this skill whenever you run Python tools or manage dependencies.

## Rules

1. **Never** run `source .venv/bin/activate`, `deactivate`, or document manual venv activation.
2. **Install/sync** with `uv sync` (or `uv sync --group dev` when dev groups exist).
3. **Run tools** with `uv run <command>` so the locked environment is used automatically.
4. **Add/remove deps** with `uv add` / `uv remove` — do not hand-edit `uv.lock`.
5. **Commit** `pyproject.toml` and `uv.lock`; **ignore** `.venv/`.

## Command reference

```bash
# Setup
uv sync

# Tests
uv run pytest
uv run pytest path/to/test_file.py
uv run pytest path/to/test_file.py::test_name -v

# Lint / format / types (when in pyproject.toml)
uv run ruff check .
uv run ruff format .
uv run mypy src

# Apps and scripts
uv run uvicorn module:app --reload --host 0.0.0.0 --port 8000
uv run python script.py

# CDK / other CLIs installed as project deps
uv run cdk synth
uv run cdk deploy --all
```

## When migrating legacy projects

If `requirements*.txt` still exist, prefer moving deps into `pyproject.toml` and using `uv sync`. Only use `uv pip install -r ...` as a transitional step.

## Containers

Development runs in isolated containers. Shell permissions assume this environment is safe for routine commands.
