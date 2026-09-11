from __future__ import annotations
from typing import Optional, List
import os
import re
import shutil
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import func

from config.settings import settings
from core.models.entities import (
    Shipment, SalesOrder, SalesOrderStatus, ShipmentStatus, ProblemType,
    UserRole, Channel, Discrepancia
)
from infrastructure.logging.audit_service import AuditService
from core.schemas.validators import ShipmentUpdateSchema


class InvalidStatusTransitionError(Exception): pass
class PermissionDeniedError(Exception): pass
class InvalidChannelError(Exception): pass
class OwnershipError(Exception): pass
class ConcurrentUpdateError(Exception): pass
class BusinessRuleError(Exception): pass
class DiscrepancyBlockedError(Exception): pass


class ShipmentService:
    def __init__(self, db: Session):
        self._db = db
        self._audit = AuditService(db)

    def _sanitize_filename(self, name: str) -> str:
        return re.sub(r'[\\/*?:"<>|\s]', '_', name)

    def _safe_float(self, value, default=0.0) -> float:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return default
            try:
                return float(value)
            except ValueError:
                return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def list_active_channels(self) -> list[Channel]:
        return self._db.query(Channel).filter(Channel.is_active == True).order_by(Channel.code).all()

    def create_sales_order(
        self,
        order_number: str,
        customer_name: str,
        channel_code: str,
        created_by_id: Optional[int] = None,
        numero_pedido_logistica: str = "",
        total_cajas_logistica: Optional[int] = None,
        agente_ventas: str = "",
        cajas: str = "",
        bolsas: str = "",
        fecha_envio: str = "",
        fecha_entrega: str = "",
        ubicacion: str = "",
        paqueteria: str = "",
        valor_mxn: str = "",
        numero_guia: str = "",
        archivo_guia: str = "",
    ) -> SalesOrder:
        channel = self._db.query(Channel).filter(
            Channel.code == channel_code, Channel.is_active == True
        ).first()
        if not channel:
            raise InvalidChannelError(f"Canal '{channel_code}' no existe o esta inactivo.")

        order = SalesOrder(
            order_number=order_number,
            customer_name=customer_name,
            channel_id=channel.id,
            created_by_id=created_by_id,
            total_cajas_logistica=total_cajas_logistica,
            numero_pedido_logistica=numero_pedido_logistica,
            agente_ventas=agente_ventas or None,
            status=SalesOrderStatus.ACTIVA,
        )
        self._db.add(order)
        self._db.flush()

        default_shipment = Shipment(
            sales_order_id=order.id,
            status=ShipmentStatus.EN_ESPERA,
            version=1,
        )
        self._db.add(default_shipment)
        self._db.flush()

        self._audit.log("SALES_ORDER_CREATED", f"SalesOrder:{order.id}", detail=order_number, user_id=created_by_id)
        self.reconciliar_totales(order.id, created_by_id)
        return order

    def list_shipments(self, user_role: UserRole, user_id: Optional[int] = None) -> list[Shipment]:
        query = self._db.query(Shipment).join(SalesOrder, Shipment.sales_order_id == SalesOrder.id)
        if not settings.ROLE_PERMISSIONS[user_role.value]["ver_todo"]:
            query = query.filter(SalesOrder.created_by_id == user_id)
        return query.order_by(Shipment.updated_at.desc()).all()

    def list_sales_orders(self, user_role: UserRole, user_id: Optional[int] = None) -> list[SalesOrder]:
        query = self._db.query(SalesOrder)
        if not settings.ROLE_PERMISSIONS[user_role.value]["ver_todo"]:
            query = query.filter(SalesOrder.created_by_id == user_id)
        return query.order_by(SalesOrder.created_at.desc()).all()

    def update_shipment_detalles(
        self,
        shipment_id: int,
        data: ShipmentUpdateSchema,
        user_role: UserRole,
        user_id: Optional[int] = None,
    ) -> Shipment:
        if not settings.ROLE_PERMISSIONS[user_role.value]["cambiar_estatus"]:
            raise PermissionDeniedError("No tienes permiso para modificar embarques.")

        shipment = self._db.get(Shipment, shipment_id)
        if not shipment:
            raise ValueError("Embarque no existe.")

        order = (
            self._db.query(SalesOrder)
            .filter(SalesOrder.id == shipment.sales_order_id)
            .with_for_update()
            .first()
        )
        if not order:
            raise ValueError("OV asociada no encontrada.")

        if order.status in (SalesOrderStatus.FACTURADA, SalesOrderStatus.CANCELADA, SalesOrderStatus.CERRADA):
            raise BusinessRuleError("La OV esta cerrada o cancelada. No se pueden modificar los embarques.")

        if shipment.version != data.version:
            raise ConcurrentUpdateError(f"El embarque fue modificado por otro operador. Tu version: {data.version}, actual: {shipment.version}.")

        total_cajas_actual = (
            self._db.query(func.coalesce(func.sum(Shipment.cajas_embarque), 0))
            .filter(Shipment.sales_order_id == order.id, Shipment.id != shipment_id)
            .scalar()
        )
        total_cajas_actual = self._safe_float(total_cajas_actual)
        nuevo_total = total_cajas_actual + data.cajas

        shipment.numero_pedido_embarque = data.numero_pedido
        shipment.cajas_embarque = data.cajas
        shipment.chofer_recibe = data.chofer
        shipment.fecha_entrega = data.fecha_entrega
        shipment.hora_entrega = getattr(data, "hora_entrega", None)
        shipment.nombre_quien_entrega = getattr(data, "nombre_quien_entrega", None)
        shipment.comentarios = getattr(data, "comentarios", None)
        shipment.version += 1

        if order.total_cajas_logistica is not None and nuevo_total >= order.total_cajas_logistica:
            order.status = SalesOrderStatus.COMPLETA
        elif nuevo_total > 0:
            order.status = SalesOrderStatus.EN_EMBARQUE
        else:
            order.status = SalesOrderStatus.ACTIVA

        self._db.flush()
        self.reconciliar_totales(order.id, user_id)
        return shipment

    def change_status(
        self,
        shipment_id: int,
        new_status: ShipmentStatus,
        user_role: UserRole,
        user_id: Optional[int] = None,
        problem_type: Optional[ProblemType] = None,
        version_expected: int = 1,
    ) -> Shipment:
        if not settings.ROLE_PERMISSIONS[user_role.value]["cambiar_estatus"]:
            raise PermissionDeniedError(f"El rol {user_role.value} no puede modificar estatus.")

        _RED_STATUSES = (ShipmentStatus.DEVOLUCION, ShipmentStatus.CANCELADO)
        if new_status in _RED_STATUSES and problem_type is None:
            raise ValueError(f"El estatus {new_status.value} requiere especificar problem_type.")

        shipment = self._db.get(Shipment, shipment_id)
        if not shipment:
            raise ValueError("Embarque no existe.")

        if not settings.ROLE_PERMISSIONS[user_role.value]["ver_todo"]:
            if shipment.sales_order.created_by_id != user_id:
                raise OwnershipError("No puedes modificar un embarque que no capturaste tu.")

        if shipment.version != version_expected:
            raise ConcurrentUpdateError(f"El embarque fue modificado por otro usuario. Tu version: {version_expected}, actual: {shipment.version}.")

        allowed = settings.STATUS_TRANSITIONS.get(shipment.status.value, ())
        if new_status.value not in allowed:
            raise InvalidStatusTransitionError(
                f"Transicion invalida: {shipment.status.value} -> {new_status.value}."
            )

        if new_status == ShipmentStatus.EN_CAMINO:
            discrepancia_activa = (
                self._db.query(Discrepancia)
                .filter(
                    Discrepancia.sales_order_id == shipment.sales_order_id,
                    Discrepancia.resuelta == False,
                )
                .first()
            )
            if discrepancia_activa:
                raise DiscrepancyBlockedError(
                    f"Despacho bloqueado: existe una discrepancia sin resolver para "
                    f"esta OV ({discrepancia_activa.comentario}). Corrige los datos "
                    f"de Embarques antes de despachar."
                )

        shipment.status = new_status
        shipment.problem_type = problem_type
        shipment.updated_by_id = user_id
        shipment.version += 1
        self._db.flush()
        self.reconciliar_totales(shipment.sales_order_id, user_id)
        return shipment

    def attach_guide(self, shipment_id: int, source_file_path: str, user_role: UserRole, user_id: Optional[int] = None) -> Shipment:
        if not settings.ROLE_PERMISSIONS[user_role.value]["cambiar_estatus"]:
            raise PermissionDeniedError("No tienes permiso para adjuntar guias.")

        shipment = self._db.get(Shipment, shipment_id)
        if not shipment:
            raise ValueError("Embarque no existe.")

        order = (
            self._db.query(SalesOrder)
            .filter(SalesOrder.id == shipment.sales_order_id)
            .with_for_update()
            .first()
        )
        if order and order.status in (SalesOrderStatus.FACTURADA, SalesOrderStatus.CANCELADA, SalesOrderStatus.CERRADA):
            raise BusinessRuleError("No se puede adjuntar guia a una OV cerrada o cancelada.")

        if not os.path.exists(source_file_path):
            raise FileNotFoundError("El archivo de origen no existe.")
        if not os.access(source_file_path, os.R_OK):
            raise PermissionError("No tienes permisos de lectura sobre el archivo de origen.")

        base_dir = os.path.join(os.getcwd(), "guias_maestras")
        os.makedirs(base_dir, exist_ok=True)

        safe_order_num = self._sanitize_filename(shipment.sales_order.order_number)
        extension = os.path.splitext(source_file_path)[1]
        dest_filename = f"guia_{safe_order_num}_shipment_{shipment.id}{extension}"
        dest_path = os.path.join(base_dir, dest_filename)

        try:
            shutil.copy2(source_file_path, dest_path)
        except OSError as e:
            raise IOError(f"Error al copiar el archivo: {e}")

        shipment.archivo_guia = dest_path
        shipment.version += 1
        self._db.flush()
        self.reconciliar_totales(shipment.sales_order_id, user_id)
        return shipment

    def download_guide(self, shipment_id: int) -> dict:
        shipment = self._db.get(Shipment, shipment_id)
        if not shipment:
            return {"ok": False, "message": "Embarque no existe."}
        if not shipment.archivo_guia or not os.path.exists(shipment.archivo_guia):
            return {"ok": False, "message": "No hay guia adjunta o el archivo fue eliminado."}
        return {"ok": True, "path": shipment.archivo_guia}

    def reconciliar_totales(self, sales_order_id: int, usuario_id: Optional[int] = None) -> dict:
        order = self._db.get(SalesOrder, sales_order_id)
        if not order:
            raise ValueError("OV no encontrada")

        total_logistica = self._safe_float(order.total_cajas_logistica)
        total_embarques = self._db.query(
            func.coalesce(func.sum(Shipment.cajas_embarque), 0)
        ).filter(Shipment.sales_order_id == sales_order_id).scalar()
        total_embarques = self._safe_float(total_embarques)

        diff_cajas = Decimal(str(total_embarques)) - Decimal(str(total_logistica))

        shipment = self._db.query(Shipment).filter(Shipment.sales_order_id == sales_order_id).first()
        num_pedido_emb = shipment.numero_pedido_embarque if shipment else None
        num_pedido_log = getattr(order, "numero_pedido_logistica", None)

        hay_discrepancia_cajas = (diff_cajas != 0)
        hay_discrepancia_pedido = bool(num_pedido_log and num_pedido_emb and num_pedido_log != num_pedido_emb)

        existing = self._db.query(Discrepancia).filter(
            Discrepancia.sales_order_id == sales_order_id,
            Discrepancia.resuelta == False
        ).first()

        if not hay_discrepancia_cajas and not hay_discrepancia_pedido:
            if existing:
                existing.resuelta = True
                existing.comentario = "Resuelta automaticamente al cuadrar totales y folios"
                self._db.flush()
            return {"estado": "CONCILIADO", "mensaje": "Totales y pedidos coinciden", "diferencia": 0.0}
        else:
            razones = []
            if hay_discrepancia_cajas:
                razones.append(f"Diferencia de {abs(diff_cajas)} cajas")
            if hay_discrepancia_pedido:
                razones.append(f"Desfase de pedido: Logistica ({num_pedido_log}) vs Embarques ({num_pedido_emb})")
            detalle_fallo = " | ".join(razones)

            if not existing:
                disc = Discrepancia(
                    sales_order_id=sales_order_id,
                    campo="LOGISTICA_VS_EMBARQUES",
                    valor_logistica=total_logistica,
                    valor_embarques=total_embarques,
                    diferencia=float(diff_cajas),
                    resuelta=False,
                    comentario=detalle_fallo,
                    fecha_deteccion=datetime.now(timezone.utc)
                )
                self._db.add(disc)
            else:
                existing.valor_logistica = total_logistica
                existing.valor_embarques = total_embarques
                existing.diferencia = float(diff_cajas)
                existing.comentario = detalle_fallo
                existing.fecha_deteccion = datetime.now(timezone.utc)
            self._db.flush()
            return {
                "estado": "DISCREPANCIA",
                "mensaje": detalle_fallo,
                "diferencia": float(diff_cajas)
            }

    def obtener_alertas(self) -> list[dict]:
        discrepancias = self._db.query(Discrepancia).filter(Discrepancia.resuelta == False).all()
        result = []
        for d in discrepancias:
            diff = Decimal(str(d.diferencia or 0))
            result.append({
                "ov_id": d.sales_order_id,
                "ov": d.sales_order.order_number,
                "total_logistica": d.valor_logistica,
                "total_embarques": d.valor_embarques,
                "diferencia": float(diff),
                "fecha": d.fecha_deteccion
            })
        return result

    def listar_discrepancias(self, resuelta: bool = False) -> list[dict]:
        discrepancias = self._db.query(Discrepancia).filter(Discrepancia.resuelta == resuelta).all()
        result = []
        for d in discrepancias:
            order = d.sales_order
            shipment = order.shipments[0] if order.shipments else None
            result.append({
                "id": d.id,
                "ov": order.order_number,
                "cliente": order.customer_name,
                "campo": d.campo,
                "valor_logistica": d.valor_logistica,
                "valor_embarques": d.valor_embarques,
                "diferencia": d.diferencia,
                "fecha": d.fecha_deteccion,
                "numero_pedido_logistica": order.numero_pedido_logistica if hasattr(order, 'numero_pedido_logistica') else None,
                "numero_pedido_embarque": shipment.numero_pedido_embarque if shipment else None,
            })
        return result

    def get_kpis(self, user_role: UserRole, user_id: Optional[int] = None) -> dict:
        shipments = self.list_shipments(user_role, user_id)
        return {
            "total": len(shipments),
            "espera": sum(1 for s in shipments if s.status == ShipmentStatus.EN_ESPERA),
            "camino": sum(1 for s in shipments if s.status == ShipmentStatus.EN_CAMINO),
            "entregados": sum(1 for s in shipments if s.status == ShipmentStatus.ENTREGADO),
            "devueltos": sum(1 for s in shipments if s.status == ShipmentStatus.DEVOLUCION),
        }
