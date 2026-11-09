#!/usr/bin/env bash
# Atajos para levantar/apagar la app. Uso: ./app.sh [comando]
set -euo pipefail
cd "$(dirname "$0")"

export UID GID="${GID:-$(id -g)}"
URL="http://localhost:${APP_PORT:-8000}"

ensure_data() { mkdir -p data; }

case "${1:-up}" in
  up)       # PC: primer plano. Ctrl+C detiene y elimina el contenedor: no queda nada corriendo.
    ensure_data
    echo "→ Abriendo en $URL  (Ctrl+C para apagar)"
    trap 'docker compose down --remove-orphans >/dev/null 2>&1 || true' EXIT
    docker compose up --build --abort-on-container-exit
    ;;
  down)     docker compose down --remove-orphans ;;
  server)   # Servidor: segundo plano + reinicio automático (configura .env antes)
    ensure_data
    [ -f .env ] || { echo "Falta .env (copia .env.example y define APP_JWT_SECRET)"; exit 1; }
    RESTART_POLICY=unless-stopped docker compose up --build -d
    docker compose ps
    ;;
  logs)     docker compose logs -f --tail=200 ;;
  status)   docker compose ps ;;
  dev)      # Sin Docker, con recarga automática (requiere uv)
    ensure_data
    exec uv run uvicorn src.main:app --reload --host 127.0.0.1 --port "${APP_PORT:-8000}"
    ;;
  test)     exec uv run pytest -q ;;
  creds)    cat data/credenciales_iniciales.txt ;;
  cli)      # ./app.sh cli reset-password admin
    shift
    if docker compose ps --status running -q app 2>/dev/null | grep -q .; then
      docker compose exec app python -m src.cli "$@"
    else
      ensure_data
      docker compose run --rm --no-deps app python -m src.cli "$@"
    fi
    ;;
  backup)   # copia consistente de la base de datos
    ensure_data
    out="data/backup-$(date +%Y%m%d-%H%M%S).db"
    python3 -c "import sqlite3,sys; s=sqlite3.connect('data/contabilidad.db'); d=sqlite3.connect(sys.argv[1]); s.backup(d); d.close()" "$out"
    echo "Backup: $out"
    ;;
  *)
    sed -n '2,3p' "$0"; echo "Comandos: up | down | server | logs | status | dev | test | creds | cli <args> | backup"; exit 1 ;;
esac
