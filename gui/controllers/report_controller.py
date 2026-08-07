from __future__ import annotations
from dataclasses import dataclass

from infrastructure.reports.excel_report_service import (
    build_consolidated_workbook, build_channel_workbook,
)
from gui.controllers.shipment_controller import ShipmentController
from core.session import SessionState


@dataclass
class OpResult:
    ok: bool
    message: str


class ReportController:
    def __init__(self, session: SessionState):
        self.session = session
        # Reutiliza ShipmentController -- el filtro de ownership vive UNA
        # sola vez (en ShipmentService.list_shipments), no se reimplementa
        # aquí. Un reporte no puede exponer más de lo que la GUI ya muestra.
        self._shipment_controller = ShipmentController(session)

    def export_consolidated(self, output_path: str) -> OpResult:
        try:
            shipments = self._shipment_controller.list_shipments()
            if not shipments:
                return OpResult(False, "No hay embarques para exportar con tu rol actual.")
            build_consolidated_workbook(shipments, output_path)
            return OpResult(True, f"Consolidado exportado: {output_path} ({len(shipments)} filas).")
        except Exception as exc:  # noqa: BLE001 — frontera GUI
            return OpResult(False, f"Error al exportar: {exc}")

    def export_channel(self, channel_code: str, output_path: str) -> OpResult:
        try:
            shipments = self._shipment_controller.list_shipments()
            count = sum(1 for s in shipments if s.channel == channel_code)
            if count == 0:
                return OpResult(False, f"No hay embarques del canal {channel_code} para exportar.")
            build_channel_workbook(shipments, channel_code, output_path)
            return OpResult(True, f"Canal {channel_code} exportado: {output_path} ({count} filas).")
        except Exception as exc:  # noqa: BLE001
            return OpResult(False, f"Error al exportar: {exc}")
