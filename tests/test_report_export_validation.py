"""
Casos de la sesión de pulido: validar la ruta ANTES de escribir, con
mensajes traducidos en vez del traceback crudo de Python/openpyxl.
"""
import os
import stat
import sys
import pytest

from gui.controllers.report_controller import ReportController
from core.session import SessionState
from core.models.entities import UserRole
from core.services.shipment_service import ShipmentService


@pytest.fixture()
def session_with_one_shipment(admin_and_operator, seeded_channels):
    admin_id = admin_and_operator["admin_id"]
    with seeded_channels() as db:
        ShipmentService(db).create_sales_order("OV-RPT-VAL-1", "Cliente", "VL", created_by_id=admin_id)
    return SessionState(user_id=admin_id, username="admin_test", full_name="Admin Test", role=UserRole.ADMIN)


def test_extension_incorrecta_se_rechaza(session_with_one_shipment, tmp_path):
    ctrl = ReportController(session_with_one_shipment)
    result = ctrl.export_consolidated(str(tmp_path / "reporte.txt"))
    assert result.ok is False
    assert ".xlsx" in result.message


def test_carpeta_inexistente_se_rechaza(session_with_one_shipment, tmp_path):
    ctrl = ReportController(session_with_one_shipment)
    result = ctrl.export_consolidated(str(tmp_path / "no_existe" / "reporte.xlsx"))
    assert result.ok is False
    assert "no existe" in result.message


def test_carpeta_sin_permiso_de_escritura_se_rechaza(session_with_one_shipment, tmp_path):
    if sys.platform.startswith("win"):
        pytest.skip("chmod de solo lectura no se comporta igual en Windows; se prueba en CI Linux.")
    if os.geteuid() == 0:
        pytest.skip("Corriendo como root: los permisos de archivo no se aplican, el test no es válido aquí.")

    carpeta_solo_lectura = tmp_path / "solo_lectura"
    carpeta_solo_lectura.mkdir()
    os.chmod(carpeta_solo_lectura, stat.S_IREAD | stat.S_IEXEC)

    try:
        ctrl = ReportController(session_with_one_shipment)
        result = ctrl.export_consolidated(str(carpeta_solo_lectura / "reporte.xlsx"))
        assert result.ok is False
        assert "permiso" in result.message.lower()
    finally:
        os.chmod(carpeta_solo_lectura, stat.S_IRWXU)  # restaurar para que tmp_path se limpie solo


def test_ruta_valida_exporta_correctamente(session_with_one_shipment, tmp_path):
    ctrl = ReportController(session_with_one_shipment)
    output = tmp_path / "reporte_valido.xlsx"
    result = ctrl.export_consolidated(str(output))
    assert result.ok is True
    assert output.exists()
