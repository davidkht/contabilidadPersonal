# Auth patterns

Generic guidance for **authentication at the HTTP/API edge** in FastAPI backends. If this project has **`docs/AUTH_CONTEXT.md`**, read that first — it overrides and extends this template with product-specific Cognito claims, routes, and flows.

## Principles

1. **Validate identity before the handler** — JWT/session checks via FastAPI `Depends`, not inline in every route body.
2. **Authorization at two levels** — edge checks (role, resource ownership) and service-layer checks for business rules.
3. **API layer does not verify JWT signatures** when API Gateway or a reverse proxy already did; app code reads trusted claims from request context.
4. **Never import domain models in route modules** for auth — use wire roles/strings at the boundary.

## Typical FastAPI patterns

- **`TokenPayload`** (or equivalent) parsed from authorizer context / middleware.
- **`RequireRole(...)`** dependency applied per route or router.
- **Resource scoping** — e.g. carrier user’s tenant id must match path parameter; raise `HTTPException(403)` at the edge when mismatch.
- **Local dev bypass** — optional stub user when `APP_ENV=dev` and an explicit env flag; must never apply in deployed environments.

## Checklist for new protected routes

- [ ] Which roles may access this route?
- [ ] Does the path include a tenant/resource id that must match the token?
- [ ] Are sensitive operations also enforced in the service layer?
- [ ] Do mutation commands include audit context (actor id, role, IP, user agent)?

## Project-specific docs

| If present, read | Content |
|------------------|---------|
| `docs/AUTH_CONTEXT.md` | Product auth flows, Cognito/OAuth, claim tables, wire shapes |
| `docs/INFRA_CONTEXT.md` | Pool, client, trigger, gateway authorizer wiring |

When project docs are missing, infer patterns from `src/core/auth.py`, `src/api/*/security.py`, and existing routes.
