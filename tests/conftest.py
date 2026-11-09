"""Configuración global de tests.

Importar ``src.api.main`` crea la ``app`` de módulo con la configuración por defecto; aquí la
aislamos (antes de cualquier import de la app) para que no escriba ``data/.jwt_secret`` ni toque
la DB real del proyecto.
"""

from __future__ import annotations

import os
import tempfile

os.environ.setdefault("APP_DATA_DIR", tempfile.mkdtemp(prefix="contab-tests-"))
os.environ.setdefault("APP_JWT_SECRET", "t" * 48)
