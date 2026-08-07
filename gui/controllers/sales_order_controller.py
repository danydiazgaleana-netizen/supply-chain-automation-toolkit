"""
Controller: traduce eventos de la GUI en llamadas a core/services.
Regla estricta: ningún `db.query`, `db.add`, ni `session.commit` aquí.
Si necesitas tocar la sesión directamente desde un controller, es señal
de que falta un método en el service correspondiente.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable

from infrastructure.db.session import get_session
from core.services.shipment_service import ShipmentService, InvalidChannelError
from core.models.entities import UserRole
from core.schemas.dto import SalesOrderDTO, sales_order_to_dto


@dataclass
class CreateOrderResult:
    ok: bool
    message: str


class SalesOrderController:
    def __init__(self, current_user_role: UserRole, current_user_id: int | None):
        self.current_user_role = current_user_role
        self.current_user_id = current_user_id

    def create_order(
        self, order_number: str, customer_name: str, channel_code: str
    ) -> CreateOrderResult:
        # Permiso de captura también se valida aquí, además del service,
        # porque el controller es el punto de entrada desde GUI: fallar rápido
        # con mensaje claro es mejor UX que dejar que la excepción del service
        # burbujee sin contexto.
        from config.settings import settings
        if not settings.ROLE_PERMISSIONS[self.current_user_role.value]["capturar"]:
            return CreateOrderResult(False, "Tu rol no tiene permiso para capturar órdenes.")

        if not order_number.strip() or not customer_name.strip():
            return CreateOrderResult(False, "Número de OV y cliente son obligatorios.")

        try:
            with get_session() as db:
                service = ShipmentService(db)
                order = service.create_sales_order(
                    order_number=order_number.strip(),
                    customer_name=customer_name.strip(),
                    channel_code=channel_code,
                    created_by_id=self.current_user_id,
                )
                # DTO construido AQUÍ, dentro del `with`, mientras `order`
                # todavía está attached a la sesión. Es lo único que sale
                # de este bloque hacia la GUI.
                dto = sales_order_to_dto(order)
                return CreateOrderResult(True, f"OV {dto.order_number} creada correctamente.")
        except InvalidChannelError as exc:
            return CreateOrderResult(False, str(exc))
        except Exception as exc:  # noqa: BLE001 — frontera GUI, se muestra al usuario
            # La excepción real ya quedó en audit_log vía AuditService.track().
            # Aquí solo se traduce a un mensaje seguro para mostrar en pantalla.
            return CreateOrderResult(False, f"Error inesperado al crear la OV: {exc}")

    def list_active_channel_codes(self) -> list[str]:
        """Fuente para el dropdown de canal en la vista — lee de la tabla
        `channels`, ya no de settings.CHANNELS (ver ADR de datos maestros)."""
        with get_session() as db:
            service = ShipmentService(db)
            return [c.code for c in service.list_active_channels()]
