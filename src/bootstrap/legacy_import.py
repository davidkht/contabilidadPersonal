"""Importa la base de datos de la app de escritorio (una tabla por persona) al esquema nuevo.

La base legacy se abre en modo solo lectura; nunca se modifica.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from src.models.enums import TipoMovimiento
from src.ports.repositories import UnitOfWork
from src.services._common import clean, to_centavos

log = logging.getLogger(__name__)

_INTERES_RE = re.compile(r"inter[eé]s", re.IGNORECASE)
_NULLISH = {"na", "n/a", "none", "-", ""}


@dataclass
class ImportReport:
    personas: int = 0
    movimientos: int = 0
    ajustes: list[str] = field(default_factory=list)
    persona_ids: list[int] = field(default_factory=list)


def _nullable(value: object) -> str | None:
    text = clean(str(value)) if value is not None else None
    return None if text is None or text.lower() in _NULLISH else text


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def import_legacy(uow: UnitOfWork, legacy_path: Path) -> ImportReport:
    report = ImportReport()
    src = sqlite3.connect(f"file:{legacy_path}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row
    try:
        tables = {r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "Deudas" not in tables:
            raise ValueError(f"{legacy_path} no parece una base de datos de la app antigua")
        for row in src.execute("SELECT * FROM Deudas ORDER BY id"):
            nombre, apellido = clean(row["nombre"]), clean(row["apellido"])
            fecha_inicio = date.fromisoformat(str(row["fecha"])[:10])
            persona_id = uow.personas.add(
                nombre=nombre,
                apellido=apellido,
                documento=_nullable(row["documento"]),
                telefono=_nullable(row["telefono"]),
                email=_nullable(row["email"]),
                interes_mensual=float(row["interes"] or 0),
                descripcion=_nullable(row["descripcion"]),
                fecha_inicio=fecha_inicio,
            )
            report.personas += 1
            report.persona_ids.append(persona_id)
            label = f"{nombre} {apellido}"

            table = f"{row['nombre']}_{row['apellido']}".replace(" ", "_")
            running = 0
            last_fecha = fecha_inicio
            if table in tables:
                movs = src.execute(f"SELECT * FROM {_quote(table)} ORDER BY id").fetchall()
                for mov in movs:
                    fecha = date.fromisoformat(str(mov["fecha"])[:10])
                    monto = to_centavos(mov["transaccion"])
                    snapshot = to_centavos(mov["deuda_total"])
                    # La app antigua guardaba el saldo tras cada movimiento; si no cuadra con la
                    # suma (correcciones manuales), se registra un ajuste explícito y auditable.
                    expected_before = snapshot - monto
                    if expected_before != running:
                        delta = expected_before - running
                        uow.movimientos.add(
                            persona_id=persona_id,
                            fecha=fecha,
                            monto_centavos=delta,
                            tipo=TipoMovimiento.AJUSTE,
                            descripcion="Ajuste de migración (corrección manual en la app antigua)",
                            creado_por=None,
                        )
                        report.ajustes.append(f"{label}: {delta / 100:+,.2f} el {fecha}")
                        running += delta
                    last_fecha = fecha
                    if monto == 0:
                        continue
                    desc = clean(mov["descripcion"]) or ""
                    tipo = (
                        TipoMovimiento.INTERES
                        if monto > 0 and _INTERES_RE.search(desc)
                        else TipoMovimiento.from_amount(monto)
                    )
                    uow.movimientos.add(
                        persona_id=persona_id,
                        fecha=fecha,
                        monto_centavos=monto,
                        tipo=tipo,
                        descripcion=desc,
                        creado_por=None,
                    )
                    running += monto
                    report.movimientos += 1
            else:
                log.warning("No existe la tabla de movimientos %s", table)

            final = to_centavos(row["monto"])
            if final != running:
                delta = final - running
                uow.movimientos.add(
                    persona_id=persona_id,
                    fecha=last_fecha,
                    monto_centavos=delta,
                    tipo=TipoMovimiento.AJUSTE,
                    descripcion="Ajuste de migración (saldo final de la app antigua)",
                    creado_por=None,
                )
                report.ajustes.append(f"{label}: {delta / 100:+,.2f} (saldo final)")
    finally:
        src.close()
    return report
