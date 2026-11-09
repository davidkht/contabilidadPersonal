"""CLI de mantenimiento: ``python -m src.cli <comando>``.

reset-password <usuario>   genera una contraseña temporal nueva (p. ej. si olvidaste la del admin)
list-users                 lista las cuentas
"""

from __future__ import annotations

import argparse
import sys

from src.bootstrap.seed import bootstrap
from src.core.config import get_settings
from src.core.dependencies import build_container
from src.services.dto.commons import MutationAuditContext
from src.services.dto.users import ListUsersQuery, ResetPasswordCommand

# La CLI se ejecuta con acceso al servidor, así que actúa como administrador del sistema.
_SYSTEM = MutationAuditContext(user_id=0, role="admin", user_agent="cli")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m src.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    reset = sub.add_parser("reset-password", help="Restablece la contraseña de un usuario")
    reset.add_argument("username")
    sub.add_parser("list-users", help="Lista las cuentas")
    args = parser.parse_args(argv)

    settings = get_settings()
    container = build_container(settings)
    bootstrap(settings, container.database)
    users = container.users.list_users(ListUsersQuery(actor=_SYSTEM))

    if args.cmd == "list-users":
        for u in users:
            estado = "activo" if u.activo else "desactivado"
            print(f"{u.username:<28} {u.role:<8} {estado:<12} {u.persona_nombre or '-'}")
        return 0

    match = next((u for u in users if u.username.lower() == args.username.lower()), None)
    if match is None:
        print(f"No existe el usuario '{args.username}'", file=sys.stderr)
        return 1
    cred = container.users.reset_password(ResetPasswordCommand(user_id=match.id, context=_SYSTEM))
    print(f"Usuario: {cred.username}\nContraseña temporal: {cred.password_temporal}")
    print("Se pedirá cambiarla en el primer ingreso.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
