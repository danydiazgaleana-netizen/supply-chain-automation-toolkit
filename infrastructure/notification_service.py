from sqlalchemy.orm import Session
from core.models.notification import Notification
from datetime import datetime, timezone

class NotificationService:
    def __init__(self, db: Session):
        self._db = db
    
    def create(self, area_origen: str, titulo: str, mensaje: str, user_id: int = None) -> Notification:
        notif = Notification(
            area_origen=area_origen,
            titulo=titulo,
            mensaje=mensaje,
            user_id=user_id
        )
        self._db.add(notif)
        self._db.flush()
        return notif
    
    def get_recent(self, limit: int = 50) -> list[Notification]:
        return self._db.query(Notification).order_by(Notification.timestamp.desc()).limit(limit).all()
    
    def mark_as_read(self, notif_id: int) -> None:
        notif = self._db.get(Notification, notif_id)
        if notif:
            notif.leida = 1
            self._db.flush()