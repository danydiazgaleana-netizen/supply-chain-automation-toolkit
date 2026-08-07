from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime

from infrastructure.db.session import get_session
from infrastructure.storage.guide_storage import save_guide_file, InvalidFileTypeError
from core.services.shipment_service import (
    ShipmentService, PermissionDeniedError, InvalidStatusTransitionError, OwnershipError,
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

    def get_kpis(self) -> dict[str, int]:
        with get_session() as db:
            service = ShipmentService(db)
            return service.get_kpis(self.session.role, self.session.user_id)

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
        except (PermissionDeniedError, InvalidStatusTransitionError, ValueError, OwnershipError) as exc:
            return OpResult(False, str(exc))

    def update_logistics(self, shipment_id: int, **fields) -> OpResult:
        try:
            with get_session() as db:
                service = ShipmentService(db)
                service.update_logistics_details(
                    shipment_id=shipment_id, user_role=self.session.role,
                    user_id=self.session.user_id, **fields,
                )
                return OpResult(True, "Datos logísticos actualizados.")
        except (PermissionDeniedError, OwnershipError, ValueError) as exc:
            return OpResult(False, str(exc))

    def update_departure(self, shipment_id: int, **fields) -> OpResult:
        try:
            with get_session() as db:
                service = ShipmentService(db)
                service.update_departure_details(
                    shipment_id=shipment_id, user_role=self.session.role,
                    user_id=self.session.user_id, **fields,
                )
                return OpResult(True, "Datos de salida actualizados.")
        except (PermissionDeniedError, OwnershipError, ValueError) as exc:
            return OpResult(False, str(exc))

    def attach_guide(self, shipment_id: int, order_number: str, source_path: str) -> OpResult:
        try:
            relative_path = save_guide_file(source_path, order_number)
        except (InvalidFileTypeError, FileNotFoundError) as exc:
            return OpResult(False, str(exc))

        try:
            with get_session() as db:
                service = ShipmentService(db)
                service.attach_guide_file(
                    shipment_id=shipment_id, user_role=self.session.role,
                    user_id=self.session.user_id, relative_path=relative_path,
                )
                return OpResult(True, "Guía PDF adjuntada correctamente.")
        except (PermissionDeniedError, OwnershipError, ValueError) as exc:
            return OpResult(False, str(exc))
