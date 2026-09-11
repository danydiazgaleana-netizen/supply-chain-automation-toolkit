"""
Punto único de acceso al engine/sesión.
"""
from __future__ import annotations
from contextlib import contextmanager
from typing import Iterator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from core.models.entities import Base


# --- FORZADO A SQLITE ---
DB_URL = "sqlite:///./wms.db"

def _ensure_sqlite_dir(db_url: str) -> None:
    if "sqlite:///" in db_url:
        db_path = db_url.replace("sqlite:///", "")
        parent = Path(db_path).parent
        if parent and not parent.exists():
            parent.mkdir(parents=True, exist_ok=True)

_ensure_sqlite_dir(DB_URL)

_engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False},
    future=True,
)

SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)


if "sqlite" in DB_URL:
    @event.listens_for(_engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def init_db() -> None:
    Base.metadata.create_all(bind=_engine)


@contextmanager
def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()