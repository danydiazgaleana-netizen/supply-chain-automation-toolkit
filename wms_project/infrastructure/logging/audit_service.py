"""
Servicio de auditoría. Todo service de negocio lo invoca; nunca se escribe
en audit_log directamente desde otro módulo.
"""
from __future__ import annotations
import traceback
from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy.orm import Session

from core.models.entities import AuditLog


class AuditService:
    def __init__(self, db: Session):
        self._db = db

    def log(
        self,
        action: str,
        entity: str,
        detail: str = "",
        user_id: Optional[int] = None,
        success: bool = True,
        error_trace: Optional[str] = None,
    ) -> None:
        entry = AuditLog(
            action=action,
            entity=entity,
            detail=detail,
            user_id=user_id,
            success=success,
            error_trace=error_trace,
        )
        self._db.add(entry)
        # flush, no commit: la transacción la controla el caller (get_session)
        self._db.flush()

    @contextmanager
    def track(self, action: str, entity: str, user_id: Optional[int] = None) -> Iterator[None]:
        """
        Context manager: registra éxito o falla automáticamente.
        Uso:
            with audit.track("SHIPMENT_STATUS_CHANGE", f"Shipment:{id}", user_id):
                # lógica que puede lanzar excepción
        La excepción SIEMPRE se re-lanza después de loggear — auditar no es
        silenciar errores.
        """
        try:
            yield
            self.log(action, entity, user_id=user_id, success=True)
        except Exception as exc:
            self.log(
                action, entity, user_id=user_id, success=False,
                error_trace="".join(traceback.format_exception(exc)),
                detail=str(exc),
            )
            raise
