# API layer design

This document describes how the HTTP API surface is structured: conventions, boundaries, and supporting patterns. It intentionally avoids cataloguing individual routes or business operations, since those evolve independently.

## Role of the API layer

The API layer is the **edge** of the system: it validates and shapes HTTP input, applies authentication and authorization rules, invokes **application services**, and returns responses in a single, predictable envelope. It does **not** own persistence, domain invariants beyond request validation, or direct access to DynamoDB / SQL / external SDKs except through injected services.

## Framework and packaging

- **FastAPI** is used for routing, dependency injection at the request boundary, OpenAPI generation, and response models.
- The codebase ships **separate FastAPI applications** (for example admin vs carrier entrypoints). Each app has its own `create_app()` factory, includes one primary router, and registers shared exception handling. This matches separate Lambdas or deployables behind different authorizers.
- **Admin route modules** live under `src/api/admin/routes/` (for example `carriers.py`, `payments.py`, `invoices.py`). A composed `APIRouter` is built in `src/api/admin/routes/__init__.py` and included from `src/api/admin/main.py`. Shared **`RequireRole`** wiring and **`mutation_audit`** (building `MutationAuditContext` for commands) live in `src/api/admin/security.py` so each file stays focused. The **carrier** app currently keeps all handlers in `src/api/carrier/routes.py`; the same layering rules apply whether routes are one file or many.
- **Pydantic v2** models define request bodies and response payloads exposed on the wire (`src/api/*/schemas.py`). They are distinct from service DTOs under `src/services/dto/`. Schemas that use **`EmailStr`** rely on the **`email-validator`** package, which is listed in **`requirements-lambda.txt`** so deployed Lambdas can import the app.
- **CORS on deployed apps**: `src/api/admin/main.py` and `src/api/carrier/main.py` call **`register_api_cors`** from `src/core/middleware/setup.py` after exception handlers and request observability middleware. API Gateway’s default CORS only answers **OPTIONS** preflight; it does **not** attach `Access-Control-Allow-*` to **GET/POST** responses from the Lambda proxy integration. Starlette **`CORSMiddleware`** adds those headers on every successful response so browsers can read JSON from a different origin (for example Vite on `http://localhost:5173`). **`ALLOWED_ORIGINS`** on Lambdas is set from the same CDK context as the API (`ecpp:corsOrigins`); see **INFRA_CONTEXT.md**.

## Standard response envelope

Successful and error responses follow a shared envelope defined in `src.core.response` (`ApiResponse`, `ResponseMeta`, pagination helpers such as `paginated`). Handlers return this type so OpenAPI and clients see a stable shape (`success`, `data`, `error`, `meta`, including optional cursor pagination under `meta.page`).

Domain failures are raised as structured exceptions in the service layer and mapped to HTTP status codes and envelope errors in `src.api.commons.register_exception_handlers`.

## Layering and imports

**Allowed in route modules**

- FastAPI types, `Depends`, HTTP exceptions where authorization or tenancy checks belong at the edge.
- API-owned modules: `src.api.*` schemas, `wire_enums`, `commons` (request context, `wire_response`, exception registration), `deps` (service getters).
- `src.core.*` (auth primitives, response types, configuration as needed).
- **Service DTOs** under `src.services.dto.*` as the **only** representation of inputs passed into services from handlers.

**Discouraged in route modules**

- Imports from **`src.models`** or **`src.db`**. The API should not construct domain models or repositories. Enum values that must cross the boundary should come from API wire enums (or plain strings carried on DTOs), not from domain enum types.

Keeping models and persistence out of routes makes handlers thin, testable, and safe to refactor when the domain or storage changes.

## Handler convention: DTO → service → envelope

Handlers follow a consistent rhythm:

1. **Build a service DTO** (query object, command object, or nested command with `request` + `context`) from path parameters, validated body models, and request-scoped metadata (for example audit or network context).
2. **Call a single service method** with that DTO as the primary input.
3. **Return** `ApiResponse` / `paginated`, mapping service **read** DTOs into wire response models where needed (see below).

Using one obvious variable name (for example `dto`) for the object passed into the service keeps reviews and onboarding consistent.

Business actions that mutate several records should still stay behind one service call. For example, QuickPay election/cancellation routes build a command DTO and call `QuickPayService`; the service owns the ruleset lookup, cutoff validation, invoice/payment updates, and audit writes. The route should not patch invoice or payment state directly.

## Handler shape (line-by-line reference)

The examples below use **illustrative** names (`ExampleService`, `ListExampleItemsQuery`, `wire_enums.ExampleStatus`, …). Replace them with your real service, DTOs, schemas, wire enums, and `get_*_service` dependency names. The **line order and responsibilities** are what matter.

### Imports (typical for a route module)

```python
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from src.api import wire_enums
from src.api.example import schemas  # your package’s schemas module
from src.api.commons import RequestContext, get_request_context, wire_response
from src.api.deps import get_example_service
from src.core.auth import ANY_ADMIN, RequireRole, TokenPayload
from src.core.response import ApiResponse, ResponseMeta, paginated
from src.services.dto.commons import MutationAuditContext
from src.services.dto.example import (
    CreateExampleItemCommand,
    CreateExampleItemRequest as CreateExampleItemRequestDto,
    GetExampleItemQuery,
    ListExampleItemsQuery,
)
from src.services.example import ExampleService

router = APIRouter()
_require_operator = RequireRole(ANY_ADMIN)


def _mutation_audit(user: TokenPayload, ctx: RequestContext) -> MutationAuditContext:
    """Inline helper; the admin app centralizes the same logic in ``security.mutation_audit``."""
    return MutationAuditContext(
        actor_id=user.sub,
        actor_role=user.role.value,
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
    )
```

### GET list: `Query` → `Depends` → query DTO → service → `paginated`

Order of parameters: **path**, **query**, then **dependencies** (`user`, `ctx`, `service`) — a common FastAPI style.

```python
@router.get(
    "/admin/example/items",
    response_model=ApiResponse[list[schemas.ExampleItem]],
    summary="List example items",
    response_model_exclude_none=True,
)
async def list_example_items(
    status: wire_enums.ExampleStatus = Query(default=wire_enums.ExampleStatus.ACTIVE),
    limit: int = Query(default=25, ge=1, le=100),
    cursor: Optional[str] = None,
    user: TokenPayload = Depends(_require_operator),
    ctx: RequestContext = Depends(get_request_context),
    example_service: ExampleService = Depends(get_example_service),
) -> ApiResponse[list[schemas.ExampleItem]]:
    dto = ListExampleItemsQuery(
        status=status.value,
        limit=limit,
        cursor=cursor,
    )
    result = example_service.list_items(dto)
    items = [wire_response(schemas.ExampleItem, row) for row in result.items]
    return paginated(
        items,
        next_cursor=result.next_cursor,
        limit=limit,
        request_id=ctx.request_id,
    )
```

- **`Query(...)`** — validates and documents query string parameters; use **`wire_enums`** for filters, then pass **`.value`** (a `str`) into the service DTO so the route never imports `src.models`.
- **`Depends(_require_operator)`** — resolves the current user / JWT payload after role checks.
- **`Depends(get_request_context)`** — request id, IP, user agent for `meta` / audit.
- **`Depends(get_example_service)`** — resolves the application service from the composition root.
- **`dto = ...`** — single service input object (here, a **query** DTO).
- **`result = example_service.list_items(dto)`** — one service call.
- **`wire_response`** — maps each read DTO row to the API schema type.
- **`paginated(...)`** — wraps list + cursor metadata in the standard envelope.

### GET one: path param → query DTO → service → `ApiResponse` + `wire_response`

```python
@router.get(
    "/admin/example/items/{item_id}",
    response_model=ApiResponse[schemas.ExampleItem],
    summary="Get one example item",
    response_model_exclude_none=True,
)
async def get_example_item(
    item_id: str,
    user: TokenPayload = Depends(_require_operator),
    ctx: RequestContext = Depends(get_request_context),
    example_service: ExampleService = Depends(get_example_service),
) -> ApiResponse[schemas.ExampleItem]:
    dto = GetExampleItemQuery(item_id=item_id)
    row = example_service.get_item(dto)
    return ApiResponse(
        data=wire_response(schemas.ExampleItem, row),
        meta=ResponseMeta(request_id=ctx.request_id),
    )
```

### POST mutation: body schema → command DTO (request + audit context) → service → `ApiResponse`

```python
@router.post(
    "/admin/example/items",
    response_model=ApiResponse[schemas.ExampleItem],
    status_code=status.HTTP_200_OK,
    summary="Create an example item",
    response_model_exclude_none=True,
)
async def create_example_item(
    body: schemas.CreateExampleItemRequest,
    user: TokenPayload = Depends(_require_operator),
    ctx: RequestContext = Depends(get_request_context),
    example_service: ExampleService = Depends(get_example_service),
) -> ApiResponse[schemas.ExampleItem]:
    dto = CreateExampleItemCommand(
        request=CreateExampleItemRequestDto(
            name=body.name,
        ),
        context=_mutation_audit(user, ctx),
    )
    row = example_service.create_item(dto)
    return ApiResponse(
        data=wire_response(schemas.ExampleItem, row),
        meta=ResponseMeta(request_id=ctx.request_id),
    )
```

- **`body: schemas.CreateExampleItemRequest`** — HTTP body validated by the **API schema** (wire types only).
- **`CreateExampleItemRequestDto`** — service-layer **request** slice of the command (often imported with an alias when the schema name collides).
- **`CreateExampleItemCommand`** — wraps `request` + **`MutationAuditContext`** for audited writes.
- **`context=_mutation_audit(user, ctx)`** — keeps the handler one line; the helper only builds `MutationAuditContext` (string `actor_role`, no `src.models`).

## Two kinds of “models” on the boundary

1. **HTTP / OpenAPI schemas** (`src/api/*/schemas.py`) — Pydantic models with `extra="forbid"` (or equivalent) tuned for JSON clients. They use **`src.api.wire_enums`**: string enums owned by the API layer whose values align with domain enums but do not live in `src.models`.
2. **Service DTOs** (`src/services/dto/`) — Pydantic models used as commands, queries, and read projections returned by services. They may still carry domain-oriented types **inside** the service layer; the API does not import those domain types to build them. When a filter or role must originate from the HTTP layer, the DTO often carries a **string** (for example status or role as `.value` from a wire enum); the **service** parses or validates into domain enums where appropriate.

## Bridging service DTOs to API schemas: `wire_response`

`src.api.commons.wire_response(schema_type, dto)` builds an API schema instance from a service read DTO by round-tripping through JSON-compatible serialization. That lets domain enums on DTOs become plain strings that match wire enums on schemas without hand-written field mappers in every handler.

Use it for response bodies that mirror DTO shape. For purely static or trivial responses (such as a minimal health payload), constructing the schema directly is acceptable.

## Request-scoped metadata

`get_request_context` (in `src.api.commons`) supplies a small **`RequestContext`** (for example request id, client IP, user agent) derived from API Gateway event data when present, with sensible fallbacks for local runs. That context is threaded into **mutation audit** DTOs (`MutationAuditContext` in `src.services.dto.commons`) so services can record who acted and from where, using **string** roles at the boundary (`actor_role` as the JWT / wire role value) and coercing inside services when domain `UserRole` is required.

## Authentication and authorization

- **`TokenPayload`** and **`RequireRole`** (from `src.core.auth`) express JWT claims and required roles at the dependency level.
- Route modules may apply additional checks (for example ensuring a carrier user’s `carrier_id` claim matches a path parameter), raising `HTTPException` when the edge policy fails.

Authorization rules that depend on business state (for example “only SUPER_ADMIN may create admins”) remain in **services**, not duplicated as the sole source of truth in routes.

**API Gateway Cognito authorizer (REST)** validates the `Authorization: Bearer …` JWT before Lambda runs. Methods are configured **without** OAuth authorization scopes, so API Gateway treats the bearer token as an **identity (ID) token** for validation purposes. Send the **ID token** from the SPA for API calls (see **AUTH_CONTEXT.md**). Role and carrier scoping after that are enforced in FastAPI (`RequireRole`, `_assert_owns_carrier`) and return **403** when the user is authenticated but not permitted — distinct from **401** from the authorizer when the token is missing or invalid.

## Service access from routes

`src.api.deps` exposes small getters (`get_*_service`) used with `Depends(...)`. Each getter resolves the implementation via the application **`injector`** / composition root (`src.core.dependencies.resolve`), which keeps construction out of handlers and allows tests to override dependencies on the FastAPI app.

## Documentation and OpenAPI

OpenAPI URLs and interactive docs paths are typically **gated by environment** (for example enabled only in local development) so production surfaces stay minimal. Route docstrings and `summary` / `description` on route decorators remain the right place to explain behavior to operators and client authors without duplicating this file.

## Summary checklist for new handlers

- [ ] For **admin** endpoints, add the handler to the appropriate file under `src/api/admin/routes/` (or introduce a new module there and include its router in `routes/__init__.py`).
- [ ] No imports from `src.models` or `src.db` in the route module.
- [ ] Inputs assembled into a **service DTO** (command or query); body/path/query use API schemas and `wire_enums` as needed.
- [ ] One **service** call; business rules and persistence live there.
- [ ] Response wrapped in **`ApiResponse`** / **`paginated`**; read DTOs mapped with **`wire_response`** when shapes align.
- [ ] Auth and resource scoping at the edge; sensitive checks also enforced in the service where appropriate.

This keeps the API layer a stable, thin façade over evolving domain and infrastructure code.
