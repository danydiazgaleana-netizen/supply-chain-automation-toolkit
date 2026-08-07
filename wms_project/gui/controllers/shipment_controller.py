from __future__ import annotations
from dataclasses import dataclass

from infrastructure.db.session import get_session
from core.services.shipment_service import (
    ShipmentService, PermissionDeniedError, InvalidStatusTransitionError,
)
from core.models.entities import ShipmentStatus, ProblemType
from core.schemas.dto import ShipmentDTO, shipment_to_dto
from core.session import SessionState


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
            # DTOs construidos dentro del `with`, mismo patrón que ya blindamos.
            return [shipment_to_dto(s) for s in shipments]

    def change_status(
        self, shipment_id: int, new_status: ShipmentStatus,
        problem_type: ProblemType | None = None,
    ) -> OpResult:
        try:
            with get_session() as db:
                service = ShipmentService(db)
                shipment = service.change_status(
                    shipment_id=shipment_id, new_status=new_status,
                    user_role=self.session.role, user_id=self.session.user_id,
                    problem_type=problem_type,
                )
                dto = shipment_to_dto(shipment)
                return OpResult(True, f"Embarque #{dto.id} actualizado a {dto.status}.")
        except (PermissionDeniedError, InvalidStatusTransitionError, ValueError) as exc:
            return OpResult(False, str(exc))
