from __future__ import annotations
from sqlalchemy.orm import Session

from core.models.entities import Notification


class NotificationService:
    def __init__(self, db: Session):
        self._db = db

    def notify(self, area_origen: str, titulo: str, mensaje: str) -> None:
        self._db.add(Notification(area_origen=area_origen, titulo=titulo, mensaje=mensaje))
        self._db.flush()

    def list_recent(self, limit: int = 50) -> list[Notification]:
        return (
            self._db.query(Notification)
            .order_by(Notification.timestamp.desc())
            .limit(limit)
            .all()
        )

    def clear_all(self) -> None:
        self._db.query(Notification).delete()
