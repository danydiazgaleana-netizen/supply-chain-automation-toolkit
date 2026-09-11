from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from infrastructure.db.session import get_session
from core.services.shipment_service import (
    ShipmentService,
    BusinessRuleError,
    ConcurrentUpdateError,
    InvalidStatusTransitionError,
    PermissionDeniedError,
    OwnershipError,
    DiscrepancyBlockedError,
)
from core.models.entities import ShipmentStatus, ProblemType
from core.schemas.dto import ShipmentDTO, shipment_to_dto
from core.schemas.validators import ShipmentUpdateSchema
from core.session import SessionState
from pydantic import ValidationError

@dataclass
class OpResult:
    ok: bool
    message: str

class ShipmentController:
    def __init__(self, session: SessionState):
        self.session = session

    def list_shipments(self) -> list[ShipmentDTO]:
        with get_session() as db:
            service = ShipmentService(db)
            shipments = service.list_shipments(self.session.role, self.session.user_id)
            return [shipment_to_dto(s) for s in shipments]

    def change_status(
        self,
        shipment_id: int,
        new_status: ShipmentStatus,
        problem_type: Optional[ProblemType] = None,
        version_expected: int = 1,
    ) -> OpResult:
        try:
            with get_session() as db:
                service = ShipmentService(db)
                shipment = service.change_status(
                    shipment_id=shipment_id,
                    new_status=new_status,
                    user_role=self.session.role,
                    user_id=self.session.user_id,
                    problem_type=problem_type,
                    version_expected=version_expected,
                )
                dto = shipment_to_dto(shipment)
                return OpResult(True, f"Estatus actualizado a {dto.status} (v{dto.version}).")
        except DiscrepancyBlockedError as exc:
            return OpResult(False, f"🔴 {exc}")
        except ConcurrentUpdateError as exc:
            return OpResult(False, f"⚠️ Conflicto de concurrencia: {exc}. Recarga la lista y vuelve a intentar.")
        except (PermissionDeniedError, InvalidStatusTransitionError, ValueError, OwnershipError, BusinessRuleError) as exc:
            return OpResult(False, str(exc))

    def update_shipment_detalles(
        self,
        shipment_id: int,
        numero_pedido: str,
        cajas: int,
        chofer: str,
        fecha_entrega: str,
        version: int,
    ) -> OpResult:
        try:
            validated = ShipmentUpdateSchema(
                numero_pedido=numero_pedido,
                cajas=cajas,
                chofer=chofer,
                fecha_entrega=fecha_entrega,
                version=version,
            )
            with get_session() as db:
                service = ShipmentService(db)
                shipment = service.update_shipment_detalles(
                    shipment_id=shipment_id,
                    data=validated,
                    user_role=self.session.role,
                    user_id=self.session.user_id,
                )
                dto = shipment_to_dto(shipment)
                return OpResult(True, f"Embarque actualizado correctamente (v{dto.version}).")
        except ValidationError as exc:
            return OpResult(False, f"Error de validación: {exc}")
        except ConcurrentUpdateError as exc:
            return OpResult(False, f"⚠️ Conflicto de concurrencia: {exc}. Recarga la lista y vuelve a intentar.")
        except (BusinessRuleError, PermissionDeniedError, OwnershipError, ValueError) as exc:
            return OpResult(False, str(exc))

    def attach_guide(self, shipment_id: int, file_path: str) -> OpResult:
        try:
            with get_session() as db:
                service = ShipmentService(db)
                shipment = service.attach_guide(shipment_id, file_path, self.session.role, self.session.user_id)
                dto = shipment_to_dto(shipment)
                return OpResult(True, f"Guía adjuntada correctamente (v{dto.version}).")
        except (FileNotFoundError, BusinessRuleError, PermissionDeniedError, PermissionError, IOError) as exc:
            return OpResult(False, str(exc))
        except Exception as exc:
            return OpResult(False, f"Error inesperado: {exc}")

    def download_guide(self, shipment_id: int) -> OpResult:
        with get_session() as db:
            service = ShipmentService(db)
            result = service.download_guide(shipment_id)
            if result.get("ok"):
                return OpResult(True, result["path"])
            return OpResult(False, result["message"])

    def get_active_alerts(self) -> list[dict]:
        with get_session() as db:
            service = ShipmentService(db)
            return service.obtener_alertas()

    def list_discrepancias(self) -> list[dict]:
        with get_session() as db:
            service = ShipmentService(db)
            return service.listar_discrepancias(resuelta=False)
