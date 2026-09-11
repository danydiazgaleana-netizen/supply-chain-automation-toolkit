"""
Regresión del bug encontrado en producción (sesión de pulido pre-entrega):
al migrar 'channel' a 'channel_code' en SalesOrderController.create_order(),
la vista gui/views/sales_order_form_view.py se quedó llamándolo con el
nombre viejo -- TypeError en cuanto el usuario daba clic en "Guardar OV".

Ningún test cubría este controller antes, así que el bug pasó varias
sesiones sin detectarse. Esta prueba llama al controller exactamente como
lo hace la vista real (mismos nombres de parámetro), para que un futuro
refactor de firma no pueda romper este flujo sin que la suite lo note.
"""
from core.models.entities import UserRole
from gui.controllers.sales_order_controller import SalesOrderController


def test_crear_ov_con_los_mismos_kwargs_que_usa_la_vista_real(admin_and_operator, seeded_channels):
    admin_id = admin_and_operator["admin_id"]
    ctrl = SalesOrderController(current_user_role=UserRole.ADMIN, current_user_id=admin_id)

    # Firma idéntica a como la llama gui/views/sales_order_form_view.py::_on_submit
    result = ctrl.create_order(
        order_number="OV-REGR-001",
        customer_name="Cliente Regresión",
        channel_code="VL",
    )
    assert result.ok is True
    assert "OV-REGR-001" in result.message


def test_crear_ov_con_canal_invalido_da_mensaje_claro(admin_and_operator, seeded_channels):
    admin_id = admin_and_operator["admin_id"]
    ctrl = SalesOrderController(current_user_role=UserRole.ADMIN, current_user_id=admin_id)

    result = ctrl.create_order(
        order_number="OV-REGR-002", customer_name="Cliente", channel_code="NO_EXISTE",
    )
    assert result.ok is False


def test_operador_sin_permiso_de_captura_no_puede_crear_ov(admin_and_operator, seeded_channels):
    from core.services.auth_service import AuthService
    from core.models.entities import UserRole as UR

    with seeded_channels() as db:
        consulta = AuthService(db).create_user("consulta1", "PasswordSegura1", "Consulta", UR.CONSULTA)
        consulta_id = consulta.id

    ctrl = SalesOrderController(current_user_role=UR.CONSULTA, current_user_id=consulta_id)
    result = ctrl.create_order(order_number="OV-REGR-003", customer_name="Cliente", channel_code="VL")
    assert result.ok is False


def test_list_active_channel_codes_regresa_los_canales_sembrados(admin_and_operator, seeded_channels):
    ctrl = SalesOrderController(current_user_role=UserRole.ADMIN, current_user_id=admin_and_operator["admin_id"])
    codes = ctrl.list_active_channel_codes()
    assert "VL" in codes
    assert "AMAZON" in codes
