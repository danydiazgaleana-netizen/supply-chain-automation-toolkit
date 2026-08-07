"""
Casos migrados de las sesiones de Embarques y canales como dato maestro:
transición de estatus, motivo obligatorio en rojo, ownership real, y FK.
"""
import pytest
from core.services.shipment_service import (
    ShipmentService, PermissionDeniedError, InvalidStatusTransitionError,
    InvalidChannelError, OwnershipError,
)
from core.models.entities import UserRole, ShipmentStatus, ProblemType, SalesOrder


def test_canal_valido_crea_ov(seeded_channels):
    with seeded_channels() as db:
        order = ShipmentService(db).create_sales_order("OV-1", "Cliente", "VL")
        assert order.channel.code == "VL"
        assert len(order.shipments) == 1
        assert order.shipments[0].status == ShipmentStatus.EN_ESPERA


def test_canal_inexistente_se_rechaza(seeded_channels):
    with seeded_channels() as db:
        with pytest.raises(InvalidChannelError):
            ShipmentService(db).create_sales_order("OV-2", "Cliente", "CANAL_FALSO")


def test_canal_inactivo_se_rechaza(seeded_channels):
    from core.models.entities import Channel
    with seeded_channels() as db:
        db.query(Channel).filter(Channel.code == "MH").update({"is_active": False})
    with seeded_channels() as db:
        with pytest.raises(InvalidChannelError):
            ShipmentService(db).create_sales_order("OV-3", "Cliente", "MH")


def test_fk_de_canal_se_aplica_a_nivel_de_base_de_datos(seeded_channels):
    """
    Regresión del bug real encontrado en la sesión de datos maestros:
    SQLite no aplica foreign keys por default. Este test falla si alguien
    quita el PRAGMA foreign_keys=ON de infrastructure/db/session.py.
    """
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        with seeded_channels() as db:
            db.add(SalesOrder(order_number="OV-ROGUE", customer_name="X", channel_id=99999))
            db.flush()


def test_transicion_de_estatus_valida(admin_and_operator, seeded_channels):
    admin_id = admin_and_operator["admin_id"]
    with seeded_channels() as db:
        svc = ShipmentService(db)
        order = svc.create_sales_order("OV-4", "Cliente", "VL", created_by_id=admin_id)
        sid = order.shipments[0].id

    with seeded_channels() as db:
        svc = ShipmentService(db)
        shipment = svc.change_status(sid, ShipmentStatus.EN_CAMINO, UserRole.ADMIN, admin_id)
        assert shipment.status == ShipmentStatus.EN_CAMINO


def test_transicion_de_estatus_invalida_se_rechaza(admin_and_operator, seeded_channels):
    """No se puede saltar de EN_ESPERA directo a ENTREGADO."""
    admin_id = admin_and_operator["admin_id"]
    with seeded_channels() as db:
        svc = ShipmentService(db)
        order = svc.create_sales_order("OV-5", "Cliente", "VL", created_by_id=admin_id)
        sid = order.shipments[0].id

    with seeded_channels() as db:
        svc = ShipmentService(db)
        with pytest.raises(InvalidStatusTransitionError):
            svc.change_status(sid, ShipmentStatus.ENTREGADO, UserRole.ADMIN, admin_id)


def test_estatus_rojo_sin_motivo_se_rechaza(admin_and_operator, seeded_channels):
    admin_id = admin_and_operator["admin_id"]
    with seeded_channels() as db:
        order = ShipmentService(db).create_sales_order("OV-6", "Cliente", "VL", created_by_id=admin_id)
        sid = order.shipments[0].id

    with seeded_channels() as db:
        with pytest.raises(ValueError):
            ShipmentService(db).change_status(sid, ShipmentStatus.DEVOLUCION, UserRole.ADMIN, admin_id)


def test_estatus_rojo_con_motivo_funciona(admin_and_operator, seeded_channels):
    admin_id = admin_and_operator["admin_id"]
    with seeded_channels() as db:
        order = ShipmentService(db).create_sales_order("OV-7", "Cliente", "VL", created_by_id=admin_id)
        sid = order.shipments[0].id

    # DEVOLUCION solo es válido desde EN_CAMINO o ENTREGADO -- hay que pasar
    # por ahí primero, respetando la misma máquina de estados que valida el
    # service (no me la puedo saltar ni en la prueba).
    with seeded_channels() as db:
        ShipmentService(db).change_status(sid, ShipmentStatus.EN_CAMINO, UserRole.ADMIN, admin_id)

    with seeded_channels() as db:
        shipment = ShipmentService(db).change_status(
            sid, ShipmentStatus.DEVOLUCION, UserRole.ADMIN, admin_id,
            problem_type=ProblemType.DANIO_MERCANCIA,
        )
        assert shipment.problem_type == ProblemType.DANIO_MERCANCIA


def test_consulta_no_puede_cambiar_estatus(admin_and_operator, seeded_channels):
    admin_id = admin_and_operator["admin_id"]
    with seeded_channels() as db:
        order = ShipmentService(db).create_sales_order("OV-8", "Cliente", "VL", created_by_id=admin_id)
        sid = order.shipments[0].id

    with seeded_channels() as db:
        with pytest.raises(PermissionDeniedError):
            ShipmentService(db).change_status(sid, ShipmentStatus.EN_CAMINO, UserRole.CONSULTA)


def test_operador_no_ve_embarques_de_otro_operador(seeded_channels):
    from core.services.auth_service import AuthService
    with seeded_channels() as db:
        auth = AuthService(db)
        op1 = auth.create_user("op1", "OperadorPass1", "Op Uno", UserRole.OPERADOR)
        op2 = auth.create_user("op2", "OperadorPass2", "Op Dos", UserRole.OPERADOR)
        op1_id, op2_id = op1.id, op2.id

    with seeded_channels() as db:
        ShipmentService(db).create_sales_order("OV-9", "Cliente de op1", "VL", created_by_id=op1_id)

    with seeded_channels() as db:
        shipments_op2 = ShipmentService(db).list_shipments(UserRole.OPERADOR, op2_id)
        assert len(shipments_op2) == 0

    with seeded_channels() as db:
        shipments_op1 = ShipmentService(db).list_shipments(UserRole.OPERADOR, op1_id)
        assert len(shipments_op1) == 1


def test_operador_no_puede_cambiar_estatus_de_embarque_ajeno(seeded_channels):
    from core.services.auth_service import AuthService
    with seeded_channels() as db:
        auth = AuthService(db)
        op1 = auth.create_user("owner", "OperadorPass1", "Owner", UserRole.OPERADOR)
        op2 = auth.create_user("intruder", "OperadorPass2", "Intruder", UserRole.OPERADOR)
        op1_id, op2_id = op1.id, op2.id

    with seeded_channels() as db:
        order = ShipmentService(db).create_sales_order("OV-10", "Cliente", "VL", created_by_id=op1_id)
        sid = order.shipments[0].id

    with seeded_channels() as db:
        with pytest.raises(PermissionDeniedError):
            ShipmentService(db).change_status(sid, ShipmentStatus.EN_CAMINO, UserRole.OPERADOR, op2_id)


def test_supervisor_ve_todos_los_embarques(admin_and_operator, seeded_channels):
    from core.services.auth_service import AuthService
    operator_id = admin_and_operator["operator_id"]

    with seeded_channels() as db:
        auth = AuthService(db)
        sup = auth.create_user("sup1", "SupervisorPass1", "Supervisor", UserRole.SUPERVISOR)
        sup_id = sup.id

    with seeded_channels() as db:
        ShipmentService(db).create_sales_order("OV-11", "Cliente de operador", "VL", created_by_id=operator_id)

    with seeded_channels() as db:
        shipments = ShipmentService(db).list_shipments(UserRole.SUPERVISOR, sup_id)
        assert len(shipments) == 1
