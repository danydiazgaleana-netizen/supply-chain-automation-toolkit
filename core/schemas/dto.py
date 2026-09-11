from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from datetime import timezone


@dataclass(frozen=True)
class SalesOrderDTO:
    id: int
    order_number: str
    customer_name: str
    channel: str
    created_at: datetime
    numero_pedido_logistica: Optional[str] = None
    total_cajas_logistica: Optional[int] = None
    agente_ventas: Optional[str] = None


@dataclass(frozen=True)
class ShipmentDTO:
    id: int
    sales_order_id: int
    order_number: str
    customer_name: str
    channel: str
    status: str
    status_color: str
    problem_type: Optional[str]
    updated_at: datetime
    numero_pedido_embarque: Optional[str] = None
    cajas_embarque: Optional[int] = None
    chofer_recibe: Optional[str] = None
    fecha_entrega: Optional[str] = None
    archivo_guia: Optional[str] = None
    version: int = 1
    numero_pedido_logistica: Optional[str] = None
    agente_ventas: Optional[str] = None
    hora_entrega: Optional[str] = None
    nombre_quien_entrega: Optional[str] = None
    comentarios: Optional[str] = None
    tiempo_en_embarques: str = "—"


@dataclass(frozen=True)
class UserDTO:
    id: int
    username: str
    full_name: str
    role: str
    is_active: bool


def sales_order_to_dto(order) -> SalesOrderDTO:
    return SalesOrderDTO(
        id=order.id, order_number=order.order_number, customer_name=order.customer_name,
        channel=order.channel.code, created_at=order.created_at,
        numero_pedido_logistica=order.numero_pedido_logistica,
        total_cajas_logistica=order.total_cajas_logistica,
        agente_ventas=order.agente_ventas,
    )


def _calcular_tiempo_transcurrido(shipment) -> str:
    """
    Tiempo desde que el pedido entró a Embarques (created_at del Shipment)
    hasta ahora, o hasta que se marcó ENTREGADO/DEVOLUCION/CANCELADO
    (usa updated_at como fin en esos casos, no sigue corriendo el reloj
    después de resuelto).
    """
    from core.models.entities import ShipmentStatus
    inicio = shipment.created_at
    if inicio is None:
        return "—"
    if inicio.tzinfo is None:
        inicio = inicio.replace(tzinfo=timezone.utc)

    if shipment.status in (ShipmentStatus.ENTREGADO, ShipmentStatus.DEVOLUCION, ShipmentStatus.CANCELADO):
        fin = shipment.updated_at
    else:
        fin = datetime.now(timezone.utc)
    if fin.tzinfo is None:
        fin = fin.replace(tzinfo=timezone.utc)

    delta = fin - inicio
    horas_totales = delta.total_seconds() / 3600
    if horas_totales < 1:
        return f"{int(delta.total_seconds() / 60)} min"
    dias = int(horas_totales // 24)
    horas = int(horas_totales % 24)
    if dias > 0:
        return f"{dias}d {horas}h"
    return f"{horas}h"


def shipment_to_dto(shipment) -> ShipmentDTO:
    from config.settings import settings
    return ShipmentDTO(
        id=shipment.id, sales_order_id=shipment.sales_order_id,
        order_number=shipment.sales_order.order_number,
        customer_name=shipment.sales_order.customer_name,
        channel=shipment.sales_order.channel.code,
        status=shipment.status.value,
        status_color=settings.STATUS_COLOR_MAP.get(shipment.status.value, "#FFFFFF"),
        problem_type=shipment.problem_type.value if shipment.problem_type else None,
        updated_at=shipment.updated_at,
        numero_pedido_embarque=shipment.numero_pedido_embarque,
        cajas_embarque=shipment.cajas_embarque,
        chofer_recibe=shipment.chofer_recibe,
        fecha_entrega=shipment.fecha_entrega,
        archivo_guia=shipment.archivo_guia,
        version=shipment.version,
        numero_pedido_logistica=shipment.sales_order.numero_pedido_logistica,
        agente_ventas=shipment.sales_order.agente_ventas,
        hora_entrega=shipment.hora_entrega,
        nombre_quien_entrega=shipment.nombre_quien_entrega,
        comentarios=shipment.comentarios,
        tiempo_en_embarques=_calcular_tiempo_transcurrido(shipment),
    )


def user_to_dto(user) -> UserDTO:
    return UserDTO(
        id=user.id, username=user.username, full_name=user.full_name,
        role=user.role.value, is_active=user.is_active,
    )
