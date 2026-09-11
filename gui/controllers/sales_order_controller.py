"""
Controller: traduce eventos de la GUI en llamadas a core/services.
Regla estricta: ningún `db.query`, `db.add`, ni `session.commit` aquí.
"""
from __future__ import annotations
from dataclasses import dataclass

from infrastructure.db.session import get_session
from core.services.shipment_service import ShipmentService, InvalidChannelError
from core.models.entities import UserRole
from core.schemas.dto import SalesOrderDTO, sales_order_to_dto


@dataclass
class CreateOrderResult:
    ok: bool
    message: str


def _parse_int_or_none(value: str) -> int | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return int(float(value))  # tolera "10" y "10.0" por igual
    except ValueError:
        return None


class SalesOrderController:
    def __init__(self, current_user_role: UserRole, current_user_id: int | None):
        self.current_user_role = current_user_role
        self.current_user_id = current_user_id

    def create_order(
        self,
        order_number: str,
        customer_name: str,
        channel: str,
        cajas: str = "",
        numero_pedido_logistica: str = "",
        agente_ventas: str = "",
        archivo_guia_path: str = "",
        # Los siguientes campos se reciben por compatibilidad con el
        # formulario de Captura Logística, pero el modelo actual NO tiene
        # columnas para persistirlos (bolsas, fechas, ubicación, paquetería,
        # valor, número de guía). Se aceptan para no romper la llamada desde
        # la vista, pero se ignoran a propósito -- documentado aquí para que
        # no se confunda con un guardado silencioso exitoso.
        bolsas: str = "",
        fecha_envio: str = "",
        fecha_entrega: str = "",
        ubicacion: str = "",
        paqueteria: str = "",
        valor_mxn: str = "",
        numero_guia: str = "",
    ) -> CreateOrderResult:
        from config.settings import settings
        if not settings.ROLE_PERMISSIONS[self.current_user_role.value]["capturar"]:
            return CreateOrderResult(False, "Tu rol no tiene permiso para capturar órdenes.")

        if not order_number.strip() or not customer_name.strip():
            return CreateOrderResult(False, "Número de OV y cliente son obligatorios.")

        # 'cajas' en el formulario de Captura Logística representa el TOTAL
        # declarado por logística para esta OV -- es lo que el motor de
        # discrepancias compara contra la suma de cajas_embarque. Se traduce
        # aquí explícitamente a total_cajas_logistica, que es el campo que
        # SalesOrder de verdad persiste.
        total_cajas_logistica = _parse_int_or_none(cajas)

        try:
            with get_session() as db:
                service = ShipmentService(db)
                order = service.create_sales_order(
                    order_number=order_number.strip(),
                    customer_name=customer_name.strip(),
                    channel_code=channel,
                    created_by_id=self.current_user_id,
                    numero_pedido_logistica=numero_pedido_logistica.strip(),
                    total_cajas_logistica=total_cajas_logistica,
                    agente_ventas=agente_ventas.strip(),
                )

                # Adjuntar guía PDF reutilizando el método ya probado del
                # service (copia el archivo Y guarda la ruta en la BD) --
                # en vez de la copia manual de la vista, que copiaba el
                # archivo pero nunca actualizaba el registro.
                if archivo_guia_path.strip():
                    default_shipment = order.shipments[0]
                    service.attach_guide(
                        shipment_id=default_shipment.id,
                        source_file_path=archivo_guia_path.strip(),
                        user_role=self.current_user_role,
                        user_id=self.current_user_id,
                    )

                dto = sales_order_to_dto(order)
                return CreateOrderResult(True, f"OV {dto.order_number} creada correctamente.")
        except InvalidChannelError as exc:
            return CreateOrderResult(False, str(exc))
        except (FileNotFoundError, PermissionError, IOError) as exc:
            # La OV ya se creó bien; solo la guía falló. Se lo decimos así,
            # no como un fallo total, para no confundir al usuario.
            return CreateOrderResult(True, f"OV {order_number} creada, pero la guía no se pudo adjuntar: {exc}")
        except Exception as exc:
            import traceback
            traceback.print_exc()
            return CreateOrderResult(False, f"Error inesperado al crear la OV: {exc}")

    def list_orders(self) -> list[SalesOrderDTO]:
        with get_session() as db:
            service = ShipmentService(db)
            orders = service.list_sales_orders(self.current_user_role, self.current_user_id)
            return [sales_order_to_dto(o) for o in orders]

    def search_orders(self, texto: str) -> list[SalesOrderDTO]:
        """
        Filtro simple en memoria sobre OV, cliente, o número de pedido de
        logística -- suficiente para el volumen de un CEDIS, no necesita
        un índice de búsqueda de verdad.
        """
        texto = (texto or "").strip().lower()
        orders = self.list_orders()
        if not texto:
            return orders
        return [
            o for o in orders
            if texto in o.order_number.lower()
            or texto in o.customer_name.lower()
            or (o.numero_pedido_logistica and texto in o.numero_pedido_logistica.lower())
        ]

    def list_active_channel_codes(self) -> list[str]:
        with get_session() as db:
            service = ShipmentService(db)
            return [c.code for c in service.list_active_channels()]
