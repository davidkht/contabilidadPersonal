# Infrastructure architecture patterns (template)

This document is a **portable template** for AWS CDK (Python) deployments that follow the same **layout and composition style** as this repository: a small **application driver**, **stack classes** as composition roots, and a **`cloud_components/` library** of reusable high-level constructs.

It is **not** a catalogue of every AWS resource in every product. Use it as a **blueprint** when starting or aligning another repo—and extend it with repo-specific modules (`rds.py`, `vpn.py`, `eks.py`, …) as they appear.

---

## 1. Goals

| Goal                                | Approach                                                                                                                    |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| **Composable stacks**               | Split by concern (identity, persistence, compute, HTTP edge) so blast radius and team ownership stay clear.                 |
| **Thin stacks, fat shared library** | `infra/stacks/*.py` wire **instances** together; repeatable patterns live in **`infra/cloud_components/`**.                 |
| **Deterministic synth**             | Required stack tags + explicit environments; CDK context for non-secret tunables aligned with **`src`/runtime `Settings`**. |
| **Safe cross-stack references**     | Grant permissions and pass ARNs/names where resources live in different stacks; avoid CloudFormation **cycles** (see §7).   |

---

## 2. Recommended directory layout under `infra/`

```
infra/
├── __init__.py                 # Package marker (may be empty)
├── account.py                  # CDK App + Stack **classes**, self-wiring (construct ids, env, tags) — see §4
├── commons.py                  # Shared constants (e.g. primary region enum)
├── iam.py                      # Optional: reusable IAM action groupings / helpers
├── required_tags.py            # Mandatory stack tags; fail-fast resolution from env/context
├── cloud_components/           # Reusable AWS abstractions (see §3)
│   ├── __init__.py             # Re-exports only modules present (keeps discovery working)
│   ├── api_gw.py
│   ├── cloudwatch.py
│   ├── cognito.py
│   ├── dynamo.py
│   ├── lambdas.py
│   ├── s3.py
│   ├── ssm.py
│   └── …                     # Optional per repo (e.g. rds.py, vpn.py, eks.py)
└── stacks/
    ├── __init__.py
    ├── security_stack.py       # IdP pools, certs, KMS keys that other stacks consume
    ├── persistence_stack.py    # Databases, buckets, queues (data plane)
    ├── application_stack.py    # Lambda, ECS tasks, Batch, Step Functions, EventBridge rules, …
    └── api_stack.py            # API Gateway / CloudFront / WAF attaching to compute
    └── network_stack.py        # VPC, subnets, route tables, VPN's, etc.
```

**Naming:** Stack class names will be **product-specific**; the **pattern** is: one **`core.App`** subclass and several **`core.Stack`** subclasses, all defined in **`account.py`** (not in `stacks/`), and all of them — the App included — are self-sufficient `@injector.singleton` + `@injector.inject` classes with **no external configuration object and no hand-written `injector.Module`**. Each stack file under `stacks/` defines the **injectable singleton constructs** (`@injector.singleton`) that live inside one of those stacks.

**Critical split — do not blur this:**

- **`account.py`** owns the `cdk.App` subclass **and** every `cdk.Stack` subclass (`PersistenceStack(cdk.Stack)`, `SecurityStack(cdk.Stack)`, …). The App resolves its own tags/config in its own `__init__` (see §4.2); each Stack takes the App as its sole injected `scope` parameter, builds its own `env=`/`tags=`, and stashes whatever small shared values (`self.prefix = ...`) constructs in that stack read off `scope`. Both the App and every Stack are decorated `@injector.singleton` + `@injector.inject` — there is nothing about them that needs to be built by hand or bound in a custom `Module`.
- **`stacks/*.py`** files **never** define a `cdk.Stack` subclass. They only define the **constructs that live inside** one specific stack (Lambdas, tables, user pools, composition/"wiring" constructs). Every one of these classes is decorated `@injector.singleton` and its `__init__` is decorated `@injector.inject`, with `scope` typed to the **specific** stack class from `account.py` (never a bare `Construct`/`cdk.Stack`).
- This is what makes the DI graph work: injector resolves a construct's dependencies purely from **type annotations**, so `scope: ApplicationStack` and `users_table: UsersTable` in a constructor signature are enough for injector to find/build the right singletons — no manual threading of `security_stack=...`, `persistence_stack=...` kwargs through every stack's `__init__`, and no hand-written provider/factory functions either (see §4 — a plain, moduleless `injector.Injector()` is enough).

**Sibling files (repo root):** `cdk.json`, `requirements.txt` / `pyproject.toml` for CDK, and a required **`app.py`** at the repo root (CDK's actual entry point per `cdk.json`'s `"app"` key) that builds the `injector.Injector()`, requests the graph's root constructs, and calls `.synth()` — see §4.2. There is **no `infra/app.py`**; because the App and every Stack are self-wiring singletons, the small amount of entry-point code has nowhere else it needs to live.

---

## 3. `cloud_components/` — project-agnostic AWS building blocks

### 3.1 Role

`infra/cloud_components/` is a **mini internal library**: opinionated wrappers around `aws-cdk-lib` that encode **defaults** (encryption, removal policies, logging, CORS helpers, alarm wiring) once. Application stacks **import and compose** these types instead of pasting long `aws_lambda.Function` or `aws_dynamodb.Table` blocks everywhere.

- **Depends on:** `aws-cdk-lib`, `constructs`, and your chosen utility packages only.
- **Must not** import `src/` application code (except indirectly via **handler strings** passed from stacks into `Lambda`, which are just strings at CDK time).
- **May** grow incrementally: not every repo ships `rds.py` or `vpn.py`; add modules as products need them and **re-export** them from `cloud_components/__init__.py` when they should participate in tooling that walks the package.

### 3.2 Module catalogue (this template’s mental model)

| Module (example)              | Typical exports / behaviour                                                                                                                                                                                                                      |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **`lambdas.py`**              | `Lambda` subclass: asset bundling excludes, optional **layer** enum (`DEFAULT`, `MSSQL`, …), `api_subpackage` stripping so each function ships only `src/api/<surface>`, log retention defaults, optional **Prewarmer**, CloudWatch alarm hooks. |
| **`api_gw.py`**               | `RestApi` / `HttpApi` subclasses, helpers to attach **Lambda proxy** integrations, **CORS** on gateway responses, optional `create_*_with_lambda` factories.                                                                                     |
| **`cognito.py`**              | `UserPool`, `UserPoolClient`, domain helpers—parameters for aliases, MFA, lambdas triggers **passed in** from stacks.                                                                                                                            |
| **`dynamo.py`**               | `Table` wrapper, global table factory, optional **auto-scaling** or **initializer** custom resources.                                                                                                                                            |
| **`s3.py`**                   | `Bucket` with block public access, versioning, lifecycle, encryption defaults.                                                                                                                                                                   |
| **`ssm.py`**                  | Parameter-store constructs and **env binding** helpers (e.g. inject parameter ARNs into task/Lambda env).                                                                                                                                        |
| **`cloudwatch.py`**           | Standard **Lambda alarms** (errors, throttles, duration) and factories.                                                                                                                                                                          |
| **`rds.py`** _(when present)_ | Subnet groups, cluster/instance, security groups, secrets rotation hooks—compose with **VPC** constructs (often defined in the same library or `stacks/network_stack.py`).                                                                       |
| **`vpn.py`** _(when present)_ | Customer gateway, VPN connection, route tables—used when Lambdas or batch jobs reach on-prem via private networking.                                                                                                                             |

**`__init__.py` policy:** Re-export only what exists so `import infra.cloud_components` never fails on missing optional modules. Repos with more files extend `__all__` accordingly.

**Reference footprint in this repository:** `infra/cloud_components/__init__.py` currently re-exports `api_gw`, `cloudwatch`, `cognito`, `dynamo`, `lambdas`, `s3`, and `ssm` only. Other repos following the same layout add modules such as **`rds.py`** or **`vpn.py`** and extend `__all__` when those constructs should be part of the shared library surface.

### 3.3 Relationship to `stacks/`

| Layer                   | Responsibility                                                                                                                        |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| **`cloud_components/`** | Generic “how to build a Lambda/Dynamo user pool/REST API with our defaults.”                                                          |
| **`stacks/`**           | “Which **named** table, which **handler** string, which **schedules**, which **authorizer**—and how stacks **reference each other**.” |

---

## 4. Dependency injection (mandatory) and entry point (root `app.py`)

This is the single most important convention in this template and the one most likely to be silently dropped if not followed literally: **every CDK construct — including the `App` and every `Stack` themselves — is wired via the [`injector`](https://pypi.org/project/injector/) library — never via manual constructor kwargs passed stack-to-stack, and never via a hand-written `injector.Module` with `@injector.provider` factory methods.** If you catch yourself writing `ApplicationStack(app, "ApplicationStack", security_stack=security_stack, persistence_stack=persistence_stack, ...)`, a `_wire_x_access(functions=[...])` helper that threads objects between stack files, or an `injector.Module` subclass with `@injector.provider` methods to construct your stacks, you have reverted to a pattern this template does not use — stop and re-read this section. A correct implementation needs **zero** custom `injector.Module` — `injector.Injector()` with no arguments is enough, because the App and every Stack know how to build themselves.

### 4.1 The rule

1. **The `cdk.App` subclass** lives in `account.py`, decorated `@injector.singleton` with `@injector.inject` on a **zero-argument** `__init__` (besides `self`). It calls `super().__init__()`, then resolves whatever app-wide config it needs (tags, mandatory env vars — see `required_tags.py`) **itself**, exposing it as a property (e.g. `.tags`). Nothing external constructs this class or feeds it a config object — `injector` builds it the same way it builds anything else with an injectable, argument-free constructor.
2. **Every `cdk.Stack` subclass** (`PersistenceStack`, `SecurityStack`, `ApplicationStack`, `ApiStack`, …) also lives in `account.py`, also decorated `@injector.singleton` + `@injector.inject`. Its **only** injected parameter is `scope`, typed to the App subclass from step 1. Inside `__init__`, it calls `super().__init__(scope, "<StackName>", env=..., tags=scope.tags)` and stashes any small shared config (`self.prefix = ...`, CDK context values) as instance attributes for constructs in that stack to read off `scope`. No stack ever takes another stack, or a config dataclass, as a constructor parameter.
3. **Every other construct** (Lambda, DynamoDB table, Cognito user pool, API Gateway, small "wiring" constructs that only grant permissions) is a class in `stacks/<concern>_stack.py` decorated `@injector.singleton`, with `__init__` decorated `@injector.inject`. Its first parameter is `scope`, typed to the **specific** `account.py` stack class it belongs to. Any other parameter is another injectable singleton — from the **same** stack file or a **different** one — and injector resolves the whole graph transitively.
4. **Cross-stack access** (e.g. an `ApplicationStack` Lambda needing a table from `PersistenceStack`, or granting IAM to a Lambda defined in `SecurityStack`) is expressed as a normal **typed constructor parameter** on the construct that needs it, not a function call threading objects around. Do the `grant_*` / `add_environment` calls directly inside the dependent construct's own `__init__`, after `super().__init__(...)`.
5. **The root-level `app.py`** (the file `cdk.json`'s `"app"` key actually runs — a sibling of `infra/`, **not** a module inside `infra/`) does nothing but: build a plain `injector.Injector()` (no `Module` argument), `container.get(...)` the App and every construct that is a **root** of the dependency graph (nothing else depends on it — typically the top-level API construct plus any "wiring"/worker constructs), then call `app.synth()`. There is no `infra/app.py` — once the App and Stacks are self-wiring singletons, there is no leftover wiring code that needs its own module.

### 4.2 Worked example (adapt names to the product — this is real, verified code from this template)

`account.py` — the App **and** every Stack, all self-wiring, all `@injector.singleton`:

```python
@injector.singleton
class MyApp(cdk.App):
    @injector.inject
    def __init__(self) -> None:
        super().__init__()
        self._tags = required_tags.resolve_tags(self)

    @property
    def tags(self) -> dict[str, str]:
        return self._tags


@injector.singleton
class PersistenceStack(cdk.Stack):
    @injector.inject
    def __init__(self, scope: MyApp) -> None:
        super().__init__(scope, "PersistenceStack", env=_stack_env(), tags=scope.tags)
        self.prefix = PROJECT_PREFIX


@injector.singleton
class ApplicationStack(cdk.Stack):
    @injector.inject
    def __init__(self, scope: MyApp) -> None:
        super().__init__(scope, "ApplicationStack", env=_stack_env(), tags=scope.tags)
```

`stacks/persistence_stack.py` — injectable constructs only, scoped to `PersistenceStack`:

```python
@injector.singleton
class UsersTable(cloud_components.Table):
    @injector.inject
    def __init__(self, scope: PersistenceStack) -> None:
        super().__init__(scope=scope, table_name=f"{scope.prefix}-main", ...)
```

`stacks/application_stack.py` — a construct that spans two stacks purely through typed params (no manual wiring function, no `security_stack=`/`persistence_stack=` kwargs anywhere):

```python
@injector.singleton
class VectorizeApiFunction(cloud_components.Lambda):
    @injector.inject
    def __init__(self, scope: ApplicationStack, users_table: UsersTable) -> None:
        super().__init__(scope=scope, id="VectorizeApiFunction", handler="api.handler.handler")
        users_table.grant_read_write_data(self)
        self.add_environment("TABLE_NAME", users_table.table_name)


@injector.singleton
class CognitoTriggerWiring(Construct):
    """Grants the SecurityStack's trigger Lambda access to a PersistenceStack table.

    Exists only so the grant runs after both stacks' resources are built, without
    SecurityStack ever importing/referencing PersistenceStack (avoids CFN cycles —
    see §7). This construct creates no CDK resources of its own.
    """

    @injector.inject
    def __init__(
        self,
        scope: ApplicationStack,
        users_table: UsersTable,
        post_confirmation_lambda: PostConfirmationLambda,
    ) -> None:
        super().__init__(scope, "CognitoTriggerWiring")
        users_table.grant_read_write_data(post_confirmation_lambda)
        post_confirmation_lambda.add_environment("TABLE_NAME", users_table.table_name)
```

Root-level `app.py` (sibling of `infra/`) — the **entire** entry point, no `Module`, no providers:

```python
def main() -> None:
    container = injector.Injector()
    app = container.get(MyApp)

    # Requesting the root construct(s) forces injector to build the entire
    # dependency graph transitively (every stack, Lambda, table, user pool, route).
    # Nothing else depends on these, so each must be requested explicitly.
    container.get(Api)
    container.get(CognitoTriggerWiring)

    app.synth()


if __name__ == "__main__":
    main()
```

### 4.3 Why this matters (do not skip)

- **No stringly-typed cross-stack plumbing.** Adding a new cross-stack dependency is a type annotation, not a new kwarg threaded through 2-3 files.
- **No `Module`/provider boilerplate.** Because the App and every Stack are themselves injectable singletons that build their own `env=`/`tags=`, there is nothing left for a custom `injector.Module` to bind — a bare `injector.Injector()` resolves the entire tree from type hints. If you find yourself writing `@injector.provider` methods just to construct a `Stack`, that's a sign the Stack class should be self-wiring instead (see 4.2).
- **Singletons by construction.** `@injector.singleton` guarantees a table/Lambda/user-pool/stack/app is built exactly once even if five other constructs depend on it — injector deduplicates by type.
- **Stack boundary violations become visible in the constructor signature.** If `SecurityStack`-scoped code should never see `PersistenceStack`, that's enforced by nobody in `security_stack.py` ever importing a `PersistenceStack`-scoped class — reviewable at a glance.
- Any implementation that manually instantiates stacks in `app.py` with cross-stack objects passed as constructor kwargs (`ApplicationStack(app, "X", security_stack=security_stack, persistence_stack=persistence_stack)`), that builds stacks via `@injector.provider` methods in a custom `Module` instead of making them self-wiring singletons, or that defines a `cdk.Stack` subclass inside a `stacks/*.py` file, **has not followed this template** — flag it and refactor to the pattern above rather than extending it.

Synth/deploy then run: `cdk synth` / `cdk deploy` with the same **`cdk.json`** `app` command pointing at the root `app.py`.

Stacks should receive **`env`** explicitly (account/region) from a small helper — see `account.py`'s `_stack_env()` pattern — so multi-region and CI assume-role behaviour stay predictable.

---

## 5. Stack boundaries (reference model)

Not every product needs four stacks; merge or split to match **lifecycle** and **IAM trust** boundaries. A **reference** split:

| Stack           | Holds                                                                                                                                             | Consumes                                                                                       |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| **Security**    | Cognito user pool + app client, trigger Lambdas **defined next to the pool**, KMS keys dedicated to auth, sometimes WAF when colocated with edge. | Nothing from persistence stacks (avoid cycles).                                                |
| **Persistence** | DynamoDB tables, S3 buckets, optionally RDS, OpenSearch—**outputs** ARNs/names via stack properties or stable construct ids.                      | Security only if unavoidable; prefer passing consumers **names/ARNs** from app context or SSM. |
| **Application** | All “business” Lambdas (API + workers), EventBridge rules, DynamoDB stream event sources, Secrets Manager **placeholders**, SQS DLQs as needed.   | Constructs from persistence + security stacks (injected).                                      |
| **API (edge)**  | API Gateway REST/HTTP APIs, custom domains, Cognito authorizers, **explicit** routes (no greedy `/{proxy+}` if you want route-level visibility).  | Lambda ARNs from application stack; user pool from security stack.                             |

**Workers** and **HTTP Lambdas** can share the **same stack** as long as IAM and deployment cadence align; split when workers need different VPC attachment, memory profiles, or deployment pipelines.

---

## 6. Runtime contract: CDK context, env vars, and `Settings`

- **CDK context** (`cdk.json`, `cdk synth -c key=value`): **non-secret** tunables—CORS allowlists, feature flags, timezone defaults, environment name. Context is read in stacks via `scope.node.try_get_context("namespace:key")`.
- **Secrets:** Prefer **Secrets Manager** or **SSM SecureString** created in CDK with **placeholder** bodies; operators **put** real values post-deploy. Pass **ARNs** into Lambda/ECS env, not secret strings.
- **Alignment:** Every env var wired in CDK should map to **one** field in **`src`/ `Settings`** (or equivalent config) so Lambda and local dev stay documented in one place.

**Shared env helper:** A private function `_shared_env(scope, tables, buckets, …)` in the application stack (or shared module) keeps **carrier/admin/worker** functions consistent—table names, region, Cognito ids **except** where omitting them breaks CloudFormation (see §7).

---

## 7. Cross-stack wiring and cyclic dependencies

Common pattern: **Cognito user pool** references **trigger Lambdas**; those Lambdas need **table names** and **IAM** granted by resources in **persistence/application** stacks. That can create **`pool → lambda → env Ref → pool`** cycles if trigger Lambdas include `USER_POOL_ID` / `CLIENT_ID` in their environment unnecessarily.

**Template rule:** Trigger Lambdas defined in **security_stack** should start with **minimal** env; a **wiring construct** in the **application stack** (same region) calls `add_environment`, `grant_read_write_data`, etc., on those function objects **after** both stacks’ resources exist—preserving **one-directional** dependencies: security defines pool + triggers; application/persistence grants data access.

Document the same pattern any time an **authoritative** resource (IdP, KMS) must reference a Lambda that also needs outputs from that resource: **split env** or use **post-instantiation** grants.

---

## 8. IAM and compliance helpers

- **`iam.py`:** Small enums or helpers for repeated action lists (`execute-api:Invoke`, SSM reads) keep policy strings consistent.
- **`required_tags.py`:** Resolve **Company / Environment / Project** (or your org’s triple) from **environment variables** and/or CDK context; **fail synth** if missing. Apply via `Stack(..., tags=...)` when using explicit stack tags in `cdk.json`.
- **Least privilege:** Prefer **grant\_** methods on L2 constructs (`table.grant_read_write_data(fn)`) over `resources: ["*"]` except for narrow Platform cases (document exceptions).

---

## 9. Lambda packaging pattern (conceptual)

The shared `Lambda` construct in **`cloud_components/lambdas.py`** typically:

- Bundles **application** code via `Code.from_asset(".", exclude=[...])`, including only `src/` and stripping **unused** `src/api/<subpackage>` trees per function.
- Prepends **`src.`** to handler paths if your Python package layout expects it.
- Attaches **Lambda layers** (dependencies built once per stack via bundling Docker image).
- Sets **timeouts**, **memory**, optional **VPC** + security group, **reserved concurrency / aliases** when needed.

Worker functions add **event sources** in the stack (EventBridge `Rule`, DynamoDB streams, SQS pollers) rather than hiding that inside the base `Lambda` class—**keeps visibility** in the stack file.

---

## 10. API Gateway pattern (conceptual)

- **Explicit resources and methods** per route (or per small group) so infrastructure reviews match OpenAPI surfaces.
- **CognitoUserPoolsAuthorizer** (or JWT authorizer for other IdPs) with cache TTL; public routes use `AuthorizationType.NONE` for defined paths only (`/health`, registration, …).
- **CORS:** Configure **gateway default CORS** for **OPTIONS** and **gateway responses** (4xx/5xx) so browser clients see consistent headers; **Lambda** must still echo **`Access-Control-Allow-Origin`** on successful responses where the framework does not add it automatically.

---

## 11. Observability

- **CloudWatch** log retention defaults on Lambda (with an escape hatch **skip** where custom resources + Cognito triggers would otherwise cycle).
- **Alarms:** Optional list on `Lambda` construction; factories in `cloudwatch.py` standardize thresholds and naming.
- **X-Ray / ADOT:** Enable at construct or stack level when the platform standard requires it—document in the repo’s ops guide.

---

## 12. Checklist for new infra work

- [ ] New construct is `@injector.singleton` + `@injector.inject`, with `scope` typed to its **specific** `account.py` Stack class — not a bare `Construct`/`cdk.Stack`, and not passed as a manual kwarg.
- [ ] New cross-stack dependency is a **typed constructor parameter** on the consuming construct, not a function threading objects between stack files, and not a new kwarg on a Stack's `__init__`.
- [ ] No `cdk.Stack` subclass was added inside `stacks/*.py` — Stack classes only ever live in `account.py`, and both the App and every Stack are self-wiring `@injector.singleton` + `@injector.inject` classes (no hand-written `injector.Module`/`@injector.provider`).
- [ ] No `infra/app.py` was added — the root-level `app.py` is the only entry point, and it stays limited to `injector.Injector()` + `container.get(...)` on graph roots + `app.synth()`.
- [ ] Root `app.py`'s `main()` requests every newly added construct that is a **root** of the graph (nothing else depends on it) via `container.get(...)`.
- [ ] New AWS pattern used in **two** places? Promote a helper into **`cloud_components/`** instead of duplicating.
- [ ] New Lambda: handler string, **correct** `api_subpackage` (or full `src` if monolith function), **layers**, **env** keys documented in app `Settings`.
- [ ] New secret: **Secrets Manager / SSM** placeholder + **grant_read** on consumers; no literals in CDK.
- [ ] Cross-stack reference: verified **no** CloudFormation cycle (especially IdP triggers).
- [ ] **Tags** applied on every new `Stack` via shared resolver.
- [ ] **Explicit** API routes (or documented exception if using proxy integration).

---

## Appendix A — Continuation prompt (for a sibling repository)

Copy everything inside the block below into a new chat in the **other** repo so the assistant can **extend** this template with that codebase’s real modules and conventions.

```text
You are continuing a shared documentation task for AWS CDK (Python) infrastructure.

1. Read the template `docs/INFRA_ARCHITECTURE_PATTERNS.md` (from the reference repo or paste it). Treat it as the canonical **structure and patterns** document unless this repo contradicts something fundamental.

2. Scan **this repo’s** `infra/` tree, especially `infra/cloud_components/` and `infra/stacks/`.

3. Update `docs/INFRA_ARCHITECTURE_PATTERNS.md` **in this repo** (create it if missing) to:
   - Replace illustrative paths like `rds.py` / `vpn.py` with **actual** files when they exist; document their responsibilities and main exports.
   - Add any **additional** stacks (e.g. `network_stack.py`, `data_lake_stack.py`) and explain how they depend on each other.
   - Document the **real** `app.py` / CDK entry: how `App` and `Stack` classes are discovered or registered, and how `injector` (or equivalent) is used.
   - Capture **repo-specific** CDK context keys (namespace prefix, examples) and how they map to runtime `Settings` / env vars.
   - Preserve **project-agnostic** wording in the reusable sections (`cloud_components` role, stack boundary template, cycle-avoidance pattern, Lambda packaging idea); move product-specific names into subsections labeled “Implementation in this repository.”

4. If `infra/cloud_components/__init__.py` exports constructs not yet described (e.g. RDS, VPC peering, EKS), add rows to §3.2’s table and short usage notes.

5. Keep `BACKEND_ARCHITECTURE_PATTERNS.md` (if present) **unchanged** unless the user asks—this task is **infra-only**.

6. Output: the **diff** or full updated `INFRA_ARCHITECTURE_PATTERNS.md` plus a one-paragraph summary of what was added compared to the template.
```

---
