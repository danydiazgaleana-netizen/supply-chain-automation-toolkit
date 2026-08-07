from __future__ import annotations
from dataclasses import dataclass

from config.settings import settings
from infrastructure.db.session import get_session
from core.services.notification_service import NotificationService
from core.session import SessionState


@dataclass(frozen=True)
class NotificationDTO:
    timestamp: str
    area_origen: str
    titulo: str
    mensaje: str


@dataclass
class OpResult:
    ok: bool
    message: str


class NotificationController:
    def __init__(self, session: SessionState):
        self.session = session

    def list_recent(self) -> list[NotificationDTO]:
        with get_session() as db:
            service = NotificationService(db)
            notifications = service.list_recent(limit=100)
            # DTO construido dentro del `with`, mismo patrón que ya blindamos
            # contra DetachedInstanceError en el resto del proyecto.
            return [
                NotificationDTO(
                    timestamp=n.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    area_origen=n.area_origen, titulo=n.titulo, mensaje=n.mensaje,
                )
                for n in notifications
            ]

    def can_clear(self) -> bool:
        # Reutilizo el permiso de gestionar_usuarios como proxy de "acción
        # administrativa destructiva" -- vaciar el historial no es una
        # operación de negocio, es limpieza operativa, y solo ADMIN debería
        # poder borrar el feed que otros roles usan para dar seguimiento.
        return settings.ROLE_PERMISSIONS[self.session.role.value]["gestionar_usuarios"]

    def clear_all(self) -> OpResult:
        if not self.can_clear():
            return OpResult(False, "Tu rol no tiene permiso para vaciar el historial.")
        with get_session() as db:
            NotificationService(db).clear_all()
        return OpResult(True, "Historial de notificaciones vaciado.")
