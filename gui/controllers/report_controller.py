from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path

from infrastructure.reports.excel_report_service import (
    build_consolidated_workbook, build_channel_workbook,
)
from gui.controllers.shipment_controller import ShipmentController
from core.session import SessionState


@dataclass
class OpResult:
    ok: bool
    message: str


def _validate_output_path(output_path: str) -> str | None:
    """
    Valida ANTES de que openpyxl intente escribir, para dar un mensaje claro
    en vez del traceback crudo de Python. Regresa un mensaje de error si algo
    está mal, o None si la ruta es escribible.
    """
    path = Path(output_path)

    if path.suffix.lower() != ".xlsx":
        return f"La ruta debe terminar en .xlsx (recibido: '{path.suffix or 'sin extensión'}')."

    parent = path.parent
    if not parent.exists():
        return f"La carpeta '{parent}' no existe."

    if not os.access(parent, os.W_OK):
        return f"No tienes permiso de escritura en la carpeta '{parent}'."

    if path.exists() and not os.access(path, os.W_OK):
        # Caso típico: el archivo está abierto en Excel y Windows lo bloquea.
        return (
            f"No se puede sobrescribir '{path.name}' — verifica que no esté "
            f"abierto en Excel u otro programa."
        )

    return None


class ReportController:
    def __init__(self, session: SessionState):
        self.session = session
        # Reutiliza ShipmentController -- el filtro de ownership vive UNA
        # sola vez (en ShipmentService.list_shipments), no se reimplementa
        # aquí. Un reporte no puede exponer más de lo que la GUI ya muestra.
        self._shipment_controller = ShipmentController(session)

    def export_consolidated(self, output_path: str) -> OpResult:
        error = _validate_output_path(output_path)
        if error:
            return OpResult(False, error)

        try:
            shipments = self._shipment_controller.list_shipments()
            if not shipments:
                return OpResult(False, "No hay embarques para exportar con tu rol actual.")
            build_consolidated_workbook(shipments, output_path)
            return OpResult(True, f"Consolidado exportado: {output_path} ({len(shipments)} filas).")
        except PermissionError:
            return OpResult(False, "Permiso denegado al escribir el archivo. Verifica que no esté abierto.")
        except OSError as exc:
            return OpResult(False, f"No se pudo escribir el archivo: {exc.strerror or exc}.")

    def export_channel(self, channel_code: str, output_path: str) -> OpResult:
        error = _validate_output_path(output_path)
        if error:
            return OpResult(False, error)

        try:
            shipments = self._shipment_controller.list_shipments()
            count = sum(1 for s in shipments if s.channel == channel_code)
            if count == 0:
                return OpResult(False, f"No hay embarques del canal {channel_code} para exportar.")
            build_channel_workbook(shipments, channel_code, output_path)
            return OpResult(True, f"Canal {channel_code} exportado: {output_path} ({count} filas).")
        except PermissionError:
            return OpResult(False, "Permiso denegado al escribir el archivo. Verifica que no esté abierto.")
        except OSError as exc:
            return OpResult(False, f"No se pudo escribir el archivo: {exc.strerror or exc}.")
