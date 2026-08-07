"""
Punto único de acceso al engine/sesión. Nadie más en el proyecto debe llamar
create_engine directamente — eso es lo que te permite, el día de mañana,
cambiar SQLite por Postgres sin tocar una sola línea fuera de este archivo.
"""
from __future__ import annotations
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from config.settings import settings
from core.models.entities import Base

# Postgres es el motor por defecto (ver ADR-001 en config/settings.py):
# el proceso real que se reemplaza tiene condiciones de carrera reales
# (Excel compartido editado simultáneamente por gerencia y embarques).
# check_same_thread=False solo aplica si se usa el fallback SQLite en local.
_engine = create_engine(
    settings.db_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.db_url else {},
    future=True,
)

SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)


if "sqlite" in settings.db_url:
    # CRÍTICO: SQLite trae foreign keys DESACTIVADO por default -- sin esto,
    # los constraints de integridad referencial (ForeignKey) en los modelos
    # son decorativos, no reales. Postgres sí los aplica siempre, por eso
    # este bug solo aparece en el fallback local y hay que forzarlo aquí.
    @event.listens_for(_engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def init_db() -> None:
    Base.metadata.create_all(bind=_engine)


@contextmanager
def get_session() -> Iterator[Session]:
    """Uso: with get_session() as db: ..."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
