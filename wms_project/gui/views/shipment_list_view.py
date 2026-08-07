"""
Vista de Embarques. Reglas de UI que reflejan reglas de negocio ya validadas
en el service (la vista NO reimplementa la validación, solo evita ofrecer
opciones inválidas para mejor UX):
- El dropdown de "siguiente estatus" solo muestra transiciones permitidas.
- Si la transición elegida es ROJA, se abre un modal pidiendo problem_type
  antes de llamar al controller.
"""
from __future__ import annotations
import customtkinter as ctk

from config.settings import settings
from core.models.entities import ShipmentStatus, ProblemType
from gui.controllers.shipment_controller import ShipmentController

_COLOR_HEX = {
    "VERDE": "#3ddc84",
    "AMARILLO": "#e0b83d",
    "ROJO": "#ff5c5c",
}


class ProblemTypeDialog(ctk.CTkToplevel):
    """Modal bloqueante: pide el motivo antes de confirmar un estatus rojo."""

    def __init__(self, master, on_confirm):
        super().__init__(master)
        self.title("Motivo requerido")
        self.geometry("360x220")
        self.resizable(False, False)
        self.grab_set()  # modal: bloquea interacción con la ventana padre

        self.on_confirm = on_confirm
        self.selected = ctk.StringVar(value=ProblemType.RETRASO.value)

        ctk.CTkLabel(
            self, text="Este estatus requiere especificar el motivo:",
            wraplength=320,
        ).pack(padx=20, pady=(20, 12))

        for pt in ProblemType:
            ctk.CTkRadioButton(
                self, text=pt.value.replace("_", " ").title(),
                variable=self.selected, value=pt.value,
            ).pack(anchor="w", padx=32, pady=4)

        ctk.CTkButton(self, text="Confirmar", command=self._confirm).pack(pady=(16, 20))

    def _confirm(self) -> None:
        self.on_confirm(ProblemType(self.selected.get()))
        self.destroy()


class ShipmentListView(ctk.CTkFrame):
    def __init__(self, master, controller: ShipmentController, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.controller = controller
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="Embarques",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        self.feedback = ctk.CTkLabel(self, text="", text_color="gray60")
        self.feedback.grid(row=1, column=0, sticky="w", pady=(0, 12))

        self.table = ctk.CTkFrame(self, fg_color="transparent")
        self.table.grid(row=2, column=0, sticky="nswe")
        self.table.grid_columnconfigure(0, weight=1)

        self._refresh()

    def _refresh(self) -> None:
        for widget in self.table.winfo_children():
            widget.destroy()

        shipments = self.controller.list_shipments()

        if not shipments:
            ctk.CTkLabel(
                self.table, text="No hay embarques para mostrar con tu rol actual.",
                text_color="gray60",
            ).grid(row=0, column=0, sticky="w")
            return

        headers = ["OV", "Cliente", "Canal", "Estatus", "Motivo", "Cambiar a"]
        for col, text in enumerate(headers):
            ctk.CTkLabel(
                self.table, text=text, font=ctk.CTkFont(weight="bold"), text_color="gray60",
            ).grid(row=0, column=col, sticky="w", padx=8, pady=(0, 8))

        for row_idx, s in enumerate(shipments, start=1):
            ctk.CTkLabel(self.table, text=s.order_number).grid(
                row=row_idx, column=0, sticky="w", padx=8, pady=4
            )
            ctk.CTkLabel(self.table, text=s.customer_name).grid(
                row=row_idx, column=1, sticky="w", padx=8, pady=4
            )
            ctk.CTkLabel(self.table, text=s.channel).grid(
                row=row_idx, column=2, sticky="w", padx=8, pady=4
            )

            badge = ctk.CTkLabel(
                self.table, text=f"● {s.status}",
                text_color=_COLOR_HEX[s.status_color],
            )
            badge.grid(row=row_idx, column=3, sticky="w", padx=8, pady=4)

            ctk.CTkLabel(
                self.table, text=s.problem_type or "—", text_color="gray60",
            ).grid(row=row_idx, column=4, sticky="w", padx=8, pady=4)

            allowed = settings.STATUS_TRANSITIONS.get(s.status, ())
            if allowed:
                var = ctk.StringVar(value="Seleccionar…")
                ctk.CTkOptionMenu(
                    self.table, values=list(allowed), variable=var, width=150,
                    command=lambda new_status, sid=s.id, var=var: self._on_status_pick(sid, new_status, var),
                ).grid(row=row_idx, column=5, sticky="w", padx=8, pady=4)
            else:
                ctk.CTkLabel(self.table, text="(estatus final)", text_color="gray50").grid(
                    row=row_idx, column=5, sticky="w", padx=8, pady=4
                )

    def _on_status_pick(self, shipment_id: int, new_status_str: str, var: ctk.StringVar) -> None:
        new_status = ShipmentStatus(new_status_str)

        if new_status in (ShipmentStatus.DEVOLUCION, ShipmentStatus.CANCELADO):
            def confirm_with_reason(problem_type: ProblemType):
                self._apply_status_change(shipment_id, new_status, problem_type)
            ProblemTypeDialog(self, on_confirm=confirm_with_reason)
        else:
            self._apply_status_change(shipment_id, new_status, None)

    def _apply_status_change(self, shipment_id, new_status, problem_type) -> None:
        result = self.controller.change_status(shipment_id, new_status, problem_type)
        self.feedback.configure(
            text=result.message, text_color="#3ddc84" if result.ok else "#ff5c5c",
        )
        self._refresh()
