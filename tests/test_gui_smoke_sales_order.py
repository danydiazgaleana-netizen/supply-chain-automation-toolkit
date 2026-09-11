"""
Prueba de humo de GUI real -- crea la ventana de captura de OV y llama al
mismo método que dispara el clic del botón "Guardar OV" (_on_submit), con
los mismos widgets reales (no mocks). Esto es lo único que hubiera detectado
el bug de producción real: la vista llamando al controller con un nombre de
parámetro que ya no existía.

Se salta automáticamente si el entorno no tiene pantalla disponible (CI
headless sin Xvfb) -- en Windows corre normal con ventana real.
"""
import pytest

try:
    import customtkinter as ctk
    _test_root = ctk.CTk()
    _test_root.destroy()
    _HAS_DISPLAY = True
except Exception:
    _HAS_DISPLAY = False

pytestmark = pytest.mark.skipif(
    not _HAS_DISPLAY, reason="Sin pantalla disponible en este entorno (headless sin Xvfb)."
)


def test_boton_guardar_ov_no_truena_con_datos_validos(admin_and_operator, seeded_channels):
    import customtkinter as ctk
    from core.models.entities import UserRole
    from core.session import SessionState
    from gui.controllers.sales_order_controller import SalesOrderController
    from gui.views.sales_order_form_view import SalesOrderFormView

    admin_id = admin_and_operator["admin_id"]
    root = ctk.CTk()
    try:
        ctrl = SalesOrderController(current_user_role=UserRole.ADMIN, current_user_id=admin_id)
        view = SalesOrderFormView(root, controller=ctrl)
        view.pack()
        root.update()

        view.entry_order_number.insert(0, "OV-GUI-SMOKE-001")
        view.entry_customer.insert(0, "Cliente Smoke Test")

        # Esto es EXACTAMENTE lo que corre cuando el usuario da clic en
        # "Guardar OV" -- mismo método, mismos widgets, sin atajos.
        view._on_submit()
        root.update()

        feedback = view.feedback_label.cget("text")
        assert "OV-GUI-SMOKE-001" in feedback
        assert "creada correctamente" in feedback
    finally:
        root.destroy()
