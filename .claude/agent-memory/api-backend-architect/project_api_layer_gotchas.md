---
name: api-layer-gotchas
description: Non-obvious traps in this repo's FastAPI layer (catch-all /api 404 route, module-level app side effects, sync handlers)
metadata:
  type: project
---

Single FastAPI app (`src/api/main.py`, `create_app(settings)`) with composed `api_router` (prefix `/api`) in `src/api/routes/__init__.py`. It ends with a catch-all `/api/{path:path}` that raises NotFound, so the frontend StaticFiles mount at `/` never answers `/api/*` with HTML.

**Why:** the contract requires JSON 404 envelopes for unknown `/api/*` paths.

**How to apply:**
- Routes added to the app *after* `create_app()` (e.g. ad-hoc routes in tests) are shadowed by the catch-all and return 404. Use `app.dependency_overrides[get_*_service]` to inject failures in tests instead.
- New route modules must be included before the catch-all in `routes/__init__.py`.
- Importing `src.api.main` builds a default-settings app; in dev that writes `data/.jwt_secret` in the repo. `tests/conftest.py` sets `APP_DATA_DIR`/`APP_JWT_SECRET` before importing to avoid that.
- Handlers are plain `def` (not async): services are sync (SQLite + Argon2), so they run in the threadpool.
- Shared test helpers live in `tests/api/_support.py` (imported as `from _support import ...`); fixtures in `tests/api/conftest.py`.
