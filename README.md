# Contabilidad personal

Control de deudas personales: **API FastAPI + SQLite** con autenticación JWT y un frontend web
ligero (JavaScript sin frameworks ni build). Un solo contenedor sirve la API (`/api`) y la web (`/`).

## Uso rápido

```bash
./app.sh          # levanta todo en primer plano → http://localhost:8000   (Ctrl+C lo apaga)
./app.sh down     # por si quedó algo (normalmente no hace falta)
```

`Ctrl+C` detiene **y elimina** el contenedor: no queda ningún servicio corriendo en segundo plano.
La primera vez:

1. Se crea `data/contabilidad.db` y se **importa** `databases/deudas.db` (la de la app de
   escritorio; se abre en solo lectura y nunca se modifica).
2. Se crea una cuenta por persona + la cuenta `admin`, con contraseñas aleatorias, en
   **`data/credenciales_iniciales.txt`** (`./app.sh creds`). Repártelas y luego borra el archivo.
   Todos deben cambiar la contraseña en su primer ingreso.

Otros comandos:

| Comando | Qué hace |
|---|---|
| `./app.sh dev` | Sin Docker, con recarga automática (`uv run uvicorn …`) |
| `./app.sh test` | Tests (`uv run pytest`) |
| `./app.sh cli reset-password admin` | Contraseña temporal nueva (si la olvidas) |
| `./app.sh cli list-users` | Lista las cuentas |
| `./app.sh backup` | Copia consistente de la base de datos en `data/` |
| `./app.sh server` | Modo servidor (ver abajo) |
| `./app.sh logs` / `status` | Logs / estado del contenedor |

Con `./app.sh dev`, la documentación interactiva de la API está en `http://localhost:8000/api/docs`.

## Servidor (homelab, Ubuntu)

```bash
git clone … && cd contabilidadPersonal
cp .env.example .env
#   APP_ENV=prod
#   APP_JWT_SECRET=<python3 -c "import secrets; print(secrets.token_urlsafe(48))">
#   APP_BIND=0.0.0.0        (o déjalo en 127.0.0.1 si usas un proxy inverso)
# Copia tu data/ del PC (o databases/deudas.db para importar desde cero)
./app.sh server           # segundo plano, reinicio automático (restart: unless-stopped)
```

- Para apagarlo: `./app.sh down`.
- **HTTPS**: el JWT viaja en cada petición; si accedes desde fuera de tu red, pon delante un proxy
  inverso con TLS (Caddy es lo más simple) o un túnel (Tailscale/Cloudflare Tunnel). Si usas proxy,
  define `FORWARDED_ALLOW_IPS` con su IP para que el bloqueo por intentos fallidos vea la IP real.
- En `prod` se desactivan `/api/docs` y el arranque falla si falta `APP_JWT_SECRET`.

## Roles

| | admin | usuario |
|---|---|---|
| Ver resumen global, todas las personas y cuentas | ✅ | ❌ |
| Crear/editar/borrar personas, registrar o borrar movimientos | ✅ | ❌ |
| Restablecer contraseñas, activar/desactivar cuentas, aplicar intereses | ✅ | ❌ |
| Ver **su propia** deuda, analítica y movimientos | — | ✅ |
| Cambiar su contraseña | ✅ | ✅ |

La autorización se aplica dos veces: en el borde HTTP (`RequireRole`) y en los servicios
(un usuario que pida otra persona recibe 404).

### Seguridad

- Contraseñas con **Argon2id** (`pwdlib`), en la misma base de datos.
- JWT HS256 con expiración (8 h por defecto). Cada token lleva una versión: cambiar o
  restablecer la contraseña, o desactivar la cuenta, **revoca todas las sesiones** de ese usuario.
- Bloqueo de 15 min tras 5 intentos fallidos; respuesta idéntica para usuario inexistente.
- Cabeceras de seguridad y CSP estricta (`'self'`, sin CDNs ni scripts inline).
- Contenedor sin root, sistema de archivos de solo lectura, sin capabilities.

## Arquitectura

```
src/
├── api/          # capa HTTP (FastAPI): rutas finas, esquemas wire, envelope, manejo de errores
├── core/         # config, seguridad (hash/JWT), auth en el borde, envelope, composition root
├── services/     # casos de uso + DTOs (reglas de negocio y autorización)
├── ports/        # contratos de repositorios (Protocol)
├── db/           # SQLite: esquema versionado, repositorios, unidad de trabajo
├── models/       # tipos de dominio
├── bootstrap/    # migraciones al arrancar, importación legacy, cuentas iniciales
└── cli.py
web/              # frontend estático (ES modules, gráficos SVG propios)
legacy/           # respaldo de la app anterior (src/, web/, main.py) — no se usa
```

Cada handler: DTO → **una** llamada a un servicio → envelope `{success, data, error, meta}`.

### Modelo de datos

La app antigua creaba **una tabla por persona** (`Mateo_Jaimes`, …). El esquema nuevo es normal:

- `personas` — datos de contacto, interés mensual.
- `movimientos` — `persona_id`, `fecha`, `monto_centavos` (con signo: + aumenta la deuda,
  − es un abono), `tipo` (`cargo`/`abono`/`interes`/`ajuste`). **El saldo se calcula** como la
  suma de movimientos; no hay un total guardado que pueda desincronizarse.
- `users` — `username`, hash, rol, `persona_id` (null para admins), versión de token, bloqueo.

Importación: donde el saldo guardado por la app antigua no cuadraba con la suma de transacciones
(una corrección manual en *Andrés Bohorquez*, −158.357,02 el 2026-03-31) se registra un movimiento
de tipo `ajuste`, de forma que todos los saldos coinciden exactamente con los de la app antigua.

### Intereses

Es la misma regla de `verificar_y_calcular_intereses()`: a las personas con tasa > 0 y 30 días o más
sin movimientos se les cobra `saldo × tasa × meses`. Ya no se ejecuta sola al abrir la app; es un
botón en el Resumen (admin). Volver a ejecutarlo no duplica el cobro.

## App de escritorio antigua

Está en `legacy/` como respaldo. Sus dependencias: `uv sync --group legacy`.
