"""
Reglas de negocio de embarques. Esta es la capa que debería quedar 100%
reutilizable cuando envuelvas esto en endpoints FastAPI: un router llamaría
exactamente a estos mismos métodos.
"""
from __future__ import annotations
from typing import Optional

from sqlalchemy.orm import Session

from config.settings import settings
from core.models.entities import Shipment, ShipmentStatus, SalesOrder, UserRole, ProblemType, Channel
from infrastructure.logging.audit_service import AuditService

# Estatus que exigen motivo explícito (badge ROJO). Ver ADR sobre problem_type
# en core/models/entities.py.
_RED_STATUSES = (ShipmentStatus.DEVOLUCION, ShipmentStatus.CANCELADO)


class InvalidStatusTransitionError(Exception):
    pass


class PermissionDeniedError(Exception):
    pass


class InvalidChannelError(Exception):
    pass


class ShipmentService:
    def __init__(self, db: Session):
        self._db = db
        self._audit = AuditService(db)

    def list_active_channels(self) -> list[Channel]:
        return self._db.query(Channel).filter(Channel.is_active == True).order_by(Channel.code).all()  # noqa: E712

    def create_sales_order(
        self, order_number: str, customer_name: str, channel_code: str,
        created_by_id: Optional[int] = None,
    ) -> SalesOrder:
        # Validación contra dato maestro real (tabla channels), no una lista
        # hardcodeada en settings. Si el canal no existe o está inactivo,
        # se rechaza aquí -- y también a nivel de DB por el FK NOT NULL.
        channel = (
            self._db.query(Channel)
            .filter(Channel.code == channel_code, Channel.is_active == True)  # noqa: E712
            .first()
        )
        if channel is None:
            raise InvalidChannelError(
                f"Canal '{channel_code}' no existe o está inactivo. "
                f"Corre 'python -m scripts.seed_channels' si es un ambiente nuevo."
            )

        order = SalesOrder(
            order_number=order_number, customer_name=customer_name, channel_id=channel.id,
            created_by_id=created_by_id,
        )
        self._db.add(order)
        self._db.flush()

        default_shipment = Shipment(sales_order_id=order.id, status=ShipmentStatus.EN_ESPERA)
        self._db.add(default_shipment)

        self._audit.log("SALES_ORDER_CREATED", f"SalesOrder:{order.id}", detail=order_number,
                         user_id=created_by_id)
        return order

    def list_shipments(self, user_role: UserRole, user_id: Optional[int] = None) -> list[Shipment]:
        """
        Ownership real, no solo documentado: OPERADOR ve únicamente los
        embarques de OVs que él mismo creó (matriz: ver_todo=False).
        SUPERVISOR/ADMIN/CONSULTA ven todo (ver_todo=True).
        """
        query = (
            self._db.query(Shipment)
            .join(SalesOrder, Shipment.sales_order_id == SalesOrder.id)
        )
        if not settings.ROLE_PERMISSIONS[user_role.value]["ver_todo"]:
            query = query.filter(SalesOrder.created_by_id == user_id)
        return query.order_by(Shipment.updated_at.desc()).all()

    def change_status(
        self,
        shipment_id: int,
        new_status: ShipmentStatus,
        user_role: UserRole,
        user_id: Optional[int] = None,
        problem_type: Optional[ProblemType] = None,
    ) -> Shipment:
        # Permiso consultado desde la matriz centralizada (settings.ROLE_PERMISSIONS),
        # no hardcodeado aquí. Esto se valida en el service, NO solo deshabilitando
        # el botón en la GUI (eso es UX, no seguridad).
        if not settings.ROLE_PERMISSIONS[user_role.value]["cambiar_estatus"]:
            raise PermissionDeniedError(f"El rol {user_role.value} no puede modificar estatus.")

        # Regla de negocio confirmada: todo estatus ROJO exige motivo explícito.
        # Sin esto, problem_type nunca se llenaría en la práctica y la mejora
        # sobre el Excel actual (que sí junta devolución/retraso/daño) sería
        # solo teórica.
        if new_status in _RED_STATUSES and problem_type is None:
            raise ValueError(
                f"El estatus {new_status.value} requiere especificar problem_type "
                f"(RETRASO / DANIO_MERCANCIA / DEVOLUCION_CLIENTE / OTRO)."
            )
        if new_status not in _RED_STATUSES and problem_type is not None:
            raise ValueError(f"problem_type no aplica para estatus {new_status.value}.")

        with self._audit.track("SHIPMENT_STATUS_CHANGE", f"Shipment:{shipment_id}", user_id):
            shipment = (
                self._db.query(Shipment)
                .join(SalesOrder, Shipment.sales_order_id == SalesOrder.id)
                .filter(Shipment.id == shipment_id)
                .first()
            )
            if shipment is None:
                raise ValueError(f"Embarque {shipment_id} no existe.")

            # Ownership: si el rol no tiene ver_todo, solo puede tocar lo que
            # su propia OV creó. Esto es lo que cierra el gap que quedó
            # documentado desde la sesión de login.
            if not settings.ROLE_PERMISSIONS[user_role.value]["ver_todo"]:
                if shipment.sales_order.created_by_id != user_id:
                    raise PermissionDeniedError(
                        "No puedes modificar un embarque que no capturaste tú."
                    )

            allowed = settings.STATUS_TRANSITIONS.get(shipment.status.value, ())
            if new_status.value not in allowed:
                raise InvalidStatusTransitionError(
                    f"Transición inválida: {shipment.status.value} -> {new_status.value}. "
                    f"Permitidas desde {shipment.status.value}: {allowed}"
                )

            shipment.status = new_status
            shipment.problem_type = problem_type
            shipment.updated_by_id = user_id
            self._db.flush()
            return shipment
