"""
Entidades ORM. Reglas de esta capa:
- Sin lógica de negocio (eso vive en services/).
- Sin imports de GUI.
- Toda entidad con timestamps de auditoría (created_at/updated_at).
"""
from __future__ import annotations
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, Integer, String, DateTime, Enum, ForeignKey, Text, Boolean
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class UserRole(str, PyEnum):
    ADMIN = "ADMIN"
    SUPERVISOR = "SUPERVISOR"
    OPERADOR = "OPERADOR"
    CONSULTA = "CONSULTA"  # solo lectura


class ShipmentStatus(str, PyEnum):
    """
    Estatus operativo real. Se mapea a color en la GUI así:
    EN_ESPERA / EN_CAMINO -> AMARILLO
    ENTREGADO             -> VERDE
    DEVOLUCION            -> ROJO  (el motivo específico va en ProblemType)
    CANCELADO             -> ROJO
    """
    EN_ESPERA = "EN_ESPERA"
    EN_CAMINO = "EN_CAMINO"
    ENTREGADO = "ENTREGADO"
    DEVOLUCION = "DEVOLUCION"
    CANCELADO = "CANCELADO"


class ProblemType(str, PyEnum):
    """
    Granularidad que el Excel actual NO tiene y que la operación necesita.
    Solo aplica cuando ShipmentStatus == DEVOLUCION. Null en cualquier otro caso.
    """
    RETRASO = "RETRASO"
    DANIO_MERCANCIA = "DANIO_MERCANCIA"
    DEVOLUCION_CLIENTE = "DEVOLUCION_CLIENTE"
    OTRO = "OTRO"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(120), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.CONSULTA)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    shipments_updated = relationship("Shipment", back_populates="updated_by_user")


class Channel(Base):
    """
    Dato maestro. Antes 'channel' era un string libre validado solo en la
    capa de aplicación (settings.CHANNELS) — sin constraint real en la base
    de datos, cualquier inserción directa o script mal hecho podía meter un
    canal inválido. Con tabla + FK, agregar un canal nuevo es un INSERT, no
    una migración de schema ni un ALTER TABLE.
    """
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False, index=True)  # ej. "VL", "AMAZON"
    name = Column(String(80), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


class SalesOrder(Base):
    """Orden de Venta (OV) — el documento raíz que dispara uno o más embarques."""
    __tablename__ = "sales_orders"

    id = Column(Integer, primary_key=True)
    order_number = Column(String(30), unique=True, nullable=False, index=True)
    customer_name = Column(String(150), nullable=False)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    shipments = relationship("Shipment", back_populates="sales_order", cascade="all, delete-orphan")
    created_by_user = relationship("User", foreign_keys=[created_by_id])
    channel = relationship("Channel")


class Shipment(Base):
    """Embarque asociado a una OV. Una OV puede tener varios embarques parciales."""
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True)
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=False)
    tracking_reference = Column(String(60), nullable=True)
    status = Column(Enum(ShipmentStatus), nullable=False, default=ShipmentStatus.EN_ESPERA)
    # Solo tiene valor cuando status == DEVOLUCION o CANCELADO. Se valida en el
    # service, no con un CHECK constraint, para mantener el mensaje de error
    # en español y controlado por nosotros.
    problem_type = Column(Enum(ProblemType), nullable=True)
    updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sales_order = relationship("SalesOrder", back_populates="shipments")
    updated_by_user = relationship("User", back_populates="shipments_updated")


class AuditLog(Base):
    """
    Bitácora persistente. No es un 'nice to have': es el registro que responde
    '¿quién cambió qué y cuándo' cuando un embarque aparece con estatus incorrecto
    y el cliente reclama. Se escribe SIEMPRE, incluso cuando la operación falla.
    """
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(80), nullable=False)          # ej. "SHIPMENT_STATUS_CHANGE"
    entity = Column(String(80), nullable=False)           # ej. "Shipment:123"
    detail = Column(Text, nullable=True)                   # payload/diff en texto
    success = Column(Boolean, nullable=False, default=True)
    error_trace = Column(Text, nullable=True)                # stacktrace si success=False
