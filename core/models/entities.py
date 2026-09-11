from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Optional, List

from sqlalchemy import (
    Column, Integer, String, DateTime, Enum, ForeignKey, Text, Boolean, Float
)
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship

Base = declarative_base()

class UserRole(str, PyEnum):
    ADMIN = "ADMIN"
    SUPERVISOR = "SUPERVISOR"
    OPERADOR = "OPERADOR"
    CONSULTA = "CONSULTA"

class ShipmentStatus(str, PyEnum):
    EN_ESPERA = "EN_ESPERA"
    EN_CAMINO = "EN_CAMINO"
    ENTREGADO = "ENTREGADO"
    DEVOLUCION = "DEVOLUCION"
    CANCELADO = "CANCELADO"

class ProblemType(str, PyEnum):
    RETRASO = "RETRASO"
    DANIO_MERCANCIA = "DANIO_MERCANCIA"
    DEVOLUCION_CLIENTE = "DEVOLUCION_CLIENTE"
    OTRO = "OTRO"

class SalesOrderStatus(str, PyEnum):
    ACTIVA = "ACTIVA"
    EN_EMBARQUE = "EN_EMBARQUE"
    COMPLETA = "COMPLETA"
    FACTURADA = "FACTURADA"
    CANCELADA = "CANCELADA"
    CERRADA = "CERRADA"

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.CONSULTA)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    shipments_updated: Mapped[List["Shipment"]] = relationship(back_populates="updated_by_user")

class Channel(Base):
    __tablename__ = "channels"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

class SalesOrder(Base):
    __tablename__ = "sales_orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    customer_name: Mapped[str] = mapped_column(String(150), nullable=False)
    channel_id: Mapped[int] = mapped_column(Integer, ForeignKey("channels.id"), nullable=False, index=True)
    created_by_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    total_cajas_logistica: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[SalesOrderStatus] = mapped_column(Enum(SalesOrderStatus), default=SalesOrderStatus.ACTIVA, nullable=False)
    shipments: Mapped[List["Shipment"]] = relationship(back_populates="sales_order", cascade="all, delete-orphan")
    created_by_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id])
    channel: Mapped["Channel"] = relationship("Channel")
    discrepancia: Mapped[Optional["Discrepancia"]] = relationship(back_populates="sales_order", uselist=False)
    numero_pedido_logistica: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    agente_ventas: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

class Shipment(Base):
    __tablename__ = "shipments"
    id: Mapped[int] = mapped_column(primary_key=True)
    sales_order_id: Mapped[int] = mapped_column(Integer, ForeignKey("sales_orders.id"), nullable=False)
    tracking_reference: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    status: Mapped[ShipmentStatus] = mapped_column(Enum(ShipmentStatus), nullable=False, default=ShipmentStatus.EN_ESPERA)
    problem_type: Mapped[Optional[ProblemType]] = mapped_column(Enum(ProblemType), nullable=True)
    updated_by_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    numero_pedido_embarque: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cajas_embarque: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chofer_recibe: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    fecha_entrega: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    hora_entrega: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    nombre_quien_entrega: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    comentarios: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    archivo_guia: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    sales_order: Mapped["SalesOrder"] = relationship(back_populates="shipments")
    updated_by_user: Mapped[Optional["User"]] = relationship(back_populates="shipments_updated")

class Discrepancia(Base):
    __tablename__ = "discrepancias"
    id = Column(Integer, primary_key=True)
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=False)
    campo = Column(String(50), nullable=False)
    valor_logistica = Column(Float, nullable=True)
    valor_embarques = Column(Float, nullable=True)
    diferencia = Column(Float, nullable=True)
    fecha_deteccion = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    resuelta = Column(Boolean, default=False)
    usuario_resolvio_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    comentario = Column(Text, nullable=True)
    sales_order = relationship("SalesOrder", back_populates="discrepancia")
    usuario_resolvio = relationship("User", foreign_keys=[usuario_resolvio_id])

class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity: Mapped[str] = mapped_column(String(80), nullable=False)
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error_trace: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    area_origen: Mapped[str] = mapped_column(String(80), nullable=False)
    titulo: Mapped[str] = mapped_column(String(150), nullable=False)
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
