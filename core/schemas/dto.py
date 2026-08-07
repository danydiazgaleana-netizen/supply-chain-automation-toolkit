"""
DTOs (Data Transfer Objects) de salida. Regla dura desde ahora:

    Ningún controller regresa un objeto ORM (Shipment, SalesOrder, User) a la
    GUI. Regresa uno de estos dataclasses, construido DENTRO del `with
    get_session()` donde el objeto ORM todavía está "attached".

Esto es lo que evita DetachedInstanceError de raíz, en vez de tener que
acordarnos de "no tocar el objeto fuera de la sesión" cada vez.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class SalesOrderDTO:
    id: int
    order_number: str
    customer_name: str
    channel: str
    created_at: datetime


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
    # Captura logística
    cajas: Optional[int]
    bolsas: Optional[int]
    fecha_envio: Optional[datetime]
    fecha_entrega_estimada: Optional[datetime]
    ubicacion_destino: Optional[str]
    paqueteria: Optional[str]
    valor_mxn: Optional[str]
    numero_guia: Optional[str]
    archivo_guia_path: Optional[str]
    # Captura de embarque / salida
    horario_entrega: Optional[str]
    nombre_quien_entrega: Optional[str]
    nombre_chofer_recibe: Optional[str]
    fecha_salida: Optional[datetime]
    hora_salida: Optional[str]
    dias_estancia: Optional[int]


@dataclass(frozen=True)
class UserDTO:
    id: int
    username: str
    full_name: str
    role: str
    is_active: bool


def sales_order_to_dto(order) -> SalesOrderDTO:
    return SalesOrderDTO(
        id=order.id, order_number=order.order_number,
        customer_name=order.customer_name, channel=order.channel.code,
        created_at=order.created_at,
    )


def shipment_to_dto(shipment) -> ShipmentDTO:
    from config.settings import settings
    return ShipmentDTO(
        id=shipment.id, sales_order_id=shipment.sales_order_id,
        order_number=shipment.sales_order.order_number,
        customer_name=shipment.sales_order.customer_name,
        channel=shipment.sales_order.channel.code,
        status=shipment.status.value,
        status_color=settings.STATUS_COLOR_MAP[shipment.status.value],
        problem_type=shipment.problem_type.value if shipment.problem_type else None,
        updated_at=shipment.updated_at,
        cajas=shipment.cajas, bolsas=shipment.bolsas,
        fecha_envio=shipment.fecha_envio,
        fecha_entrega_estimada=shipment.fecha_entrega_estimada,
        ubicacion_destino=shipment.ubicacion_destino,
        paqueteria=shipment.paqueteria, valor_mxn=shipment.valor_mxn,
        numero_guia=shipment.numero_guia, archivo_guia_path=shipment.archivo_guia_path,
        horario_entrega=shipment.horario_entrega,
        nombre_quien_entrega=shipment.nombre_quien_entrega,
        nombre_chofer_recibe=shipment.nombre_chofer_recibe,
        fecha_salida=shipment.fecha_salida, hora_salida=shipment.hora_salida,
        dias_estancia=shipment.dias_estancia,
    )


def user_to_dto(user) -> UserDTO:
    return UserDTO(
        id=user.id, username=user.username, full_name=user.full_name,
        role=user.role.value, is_active=user.is_active,
    )
