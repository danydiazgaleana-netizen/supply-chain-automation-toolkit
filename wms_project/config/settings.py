"""
Configuración centralizada. Todo lo que cambia entre entornos (dev/staging/prod)
vive aquí y NUNCA hardcodeado en services o repositories.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    # ADR-001: se migró el default de SQLite a Postgres.
    # Motivo: el proceso real que se reemplaza es un Excel compartido editado
    # por gerencia y embarques SIMULTÁNEAMENTE, causando fórmulas rotas y datos
    # movidos por condiciones de carrera. SQLite serializa escrituras a nivel
    # de archivo y no resuelve ese problema — Postgres sí, vía locking a nivel
    # de fila y transacciones ACID. SQLite se mantiene como fallback de
    # desarrollo local rápido (WMS_DB_URL=sqlite:///... si se necesita).
    db_url: str = os.getenv(
        "WMS_DB_URL",
        "postgresql+psycopg2://wms_user:wms_pass@localhost:5432/wms_db",
    )
    reports_dir: Path = BASE_DIR / "generated_reports"
    log_level: str = os.getenv("WMS_LOG_LEVEL", "INFO")
    app_name: str = "WMS Control de Embarques"

    # Canales logísticos válidos. Definidos aquí, no como strings sueltos
    # regados por el código — si mañana agregas un canal, se edita en un solo lugar.
    CHANNELS: tuple[str, ...] = ("VL", "PEGE", "TIAU", "MUESTRAS", "AMAZON", "MH")

    # Máquina de estados válida para el estatus de un embarque.
    STATUS_TRANSITIONS: dict[str, tuple[str, ...]] = None

    # Mapeo de estatus operativo -> color de badge visual. La gerencia ya
    # reconoce este código de 3 colores desde el Excel actual; no se cambia
    # el hábito visual, solo se enriquece por debajo con problem_type cuando
    # el color es ROJO (ver core/models/entities.py::ProblemType).
    STATUS_COLOR_MAP: dict[str, str] = None

    # Matriz de permisos por rol, confirmada con el usuario. Toda validación
    # de permisos en services/ debe consultar esto — nunca hardcodear "if role
    # == ...' disperso por el código.
    ROLE_PERMISSIONS: dict[str, dict[str, bool]] = None

    def __post_init__(self):
        object.__setattr__(self, "STATUS_TRANSITIONS", {
            "EN_ESPERA": ("EN_CAMINO", "CANCELADO"),
            "EN_CAMINO": ("ENTREGADO", "DEVOLUCION"),
            "ENTREGADO": ("DEVOLUCION",),
            "DEVOLUCION": (),
            "CANCELADO": (),
        })
        object.__setattr__(self, "STATUS_COLOR_MAP", {
            "EN_ESPERA": "AMARILLO",
            "EN_CAMINO": "AMARILLO",
            "ENTREGADO": "VERDE",
            "DEVOLUCION": "ROJO",
            "CANCELADO": "ROJO",
        })
        object.__setattr__(self, "ROLE_PERMISSIONS", {
            "ADMIN":      {"ver_todo": True,  "capturar": True,  "cambiar_estatus": True,  "corregir_anular": True,  "gestionar_usuarios": True},
            "SUPERVISOR": {"ver_todo": True,  "capturar": False, "cambiar_estatus": True,  "corregir_anular": True,  "gestionar_usuarios": False},
            "OPERADOR":   {"ver_todo": False, "capturar": True,  "cambiar_estatus": True,  "corregir_anular": False, "gestionar_usuarios": False},
            "CONSULTA":   {"ver_todo": True,  "capturar": False, "cambiar_estatus": False, "corregir_anular": False, "gestionar_usuarios": False},
        })


settings = Settings()
