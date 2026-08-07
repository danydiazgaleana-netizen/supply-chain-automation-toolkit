"""
Vista de Embarques. Reglas de UI que reflejan reglas de negocio ya validadas
en el service (la vista NO reimplementa la validación, solo evita ofrecer
opciones inválidas para mejor UX):
- El dropdown de "siguiente estatus" solo muestra transiciones permitidas.
- Si la transición elegida es ROJA, se abre un modal pidiendo problem_type
  antes de llamar al controller.
- El modal de "Detalle" agrupa captura logística y de salida por separado,
  reflejando los dos momentos reales de la operación (no es un solo form
  gigante de 15 campos).
"""
from __future__ import annotations
from tkinter import filedialog
import customtkinter as ctk

from config.settings import settings
from core.models.entities import ShipmentStatus, ProblemType
from gui.controllers.shipment_controller import ShipmentController

_COLOR_HEX = {
    "VERDE": "#3ddc84",
    "AMARILLO": "#e0b83d",
    "ROJO": "#ff5c5c",
}

_KPI_LABELS = {
    "total": "Total", "EN_ESPERA": "En espera", "EN_CAMINO": "En camino",
    "ENTREGADO": "Entregados", "DEVOLUCION": "Devoluciones",
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


class ShipmentDetailDialog(ctk.CTkToplevel):
    """
    Modal con dos secciones: captura logística (etapa 1) y captura de
    salida/embarque (etapa 2), más adjuntar guía PDF. Se guardan por
    separado -- cada sección llama a su propio método del controller,
    porque en la operación real no siempre se llenan al mismo tiempo
    (logística captura al generar el pedido; embarques captura al despachar).
    """

    def __init__(self, master, controller: ShipmentController, shipment, on_saved):
        super().__init__(master)
        self.controller = controller
        self.shipment = shipment
        self.on_saved = on_saved

        self.title(f"Detalle · OV {shipment.order_number}")
        self.geometry("520x640")
        self.grab_set()

        scroll = ctk.CTkScrollableFrame(self, label_text="Captura logística")
        scroll.pack(fill="both", expand=True, padx=16, pady=(16, 8))
        scroll.grid_columnconfigure(1, weight=1)

        self.e_cajas = self._field(scroll, "Cajas", 0, shipment.cajas)
        self.e_bolsas = self._field(scroll, "Bolsas", 1, shipment.bolsas)
        self.e_ubicacion = self._field(scroll, "Ubicación destino", 2, shipment.ubicacion_destino)
        self.e_paqueteria = self._field(scroll, "Paquetería", 3, shipment.paqueteria)
        self.e_valor = self._field(scroll, "Valor ($MXN)", 4, shipment.valor_mxn)
        self.e_guia = self._field(scroll, "Número de guía", 5, shipment.numero_guia)

        ctk.CTkButton(scroll, text="Guardar captura logística", command=self._save_logistics).grid(
            row=6, column=0, columnspan=2, sticky="we", pady=(12, 4)
        )

        guia_row = ctk.CTkFrame(scroll, fg_color="transparent")
        guia_row.grid(row=7, column=0, columnspan=2, sticky="we", pady=(4, 12))
        ctk.CTkButton(guia_row, text="📎 Adjuntar guía PDF", width=160, command=self._attach_pdf).pack(side="left")
        self.lbl_guia = ctk.CTkLabel(
            guia_row, text=shipment.archivo_guia_path or "Sin archivo adjunto", text_color="gray60",
        )
        self.lbl_guia.pack(side="left", padx=10)

        ctk.CTkLabel(scroll, text="Captura de salida / embarque", font=ctk.CTkFont(weight="bold")).grid(
            row=8, column=0, columnspan=2, sticky="w", pady=(16, 8)
        )
        self.e_horario = self._field(scroll, "Horario entrega", 9, shipment.horario_entrega)
        self.e_quien_entrega = self._field(scroll, "Quién entrega", 10, shipment.nombre_quien_entrega)
        self.e_chofer = self._field(scroll, "Chofer (recibe)", 11, shipment.nombre_chofer_recibe)
        self.e_hora_salida = self._field(scroll, "Hora de salida", 12, shipment.hora_salida)
        self.e_dias_estancia = self._field(scroll, "Días de estancia", 13, shipment.dias_estancia)

        ctk.CTkButton(scroll, text="Guardar captura de salida", command=self._save_departure).grid(
            row=14, column=0, columnspan=2, sticky="we", pady=(12, 4)
        )

        self.feedback = ctk.CTkLabel(self, text="", text_color="gray60")
        self.feedback.pack(pady=(0, 12))

    def _field(self, parent, label, row, value):
        ctk.CTkLabel(parent, text=label).grid(row=row, column=0, sticky="w", padx=(4, 8), pady=6)
        entry = ctk.CTkEntry(parent)
        if value is not None:
            entry.insert(0, str(value))
        entry.grid(row=row, column=1, sticky="we", pady=6)
        return entry

    def _to_int_or_none(self, raw: str):
        raw = raw.strip()
        return int(raw) if raw.isdigit() else None

    def _save_logistics(self) -> None:
        result = self.controller.update_logistics(
            self.shipment.id,
            cajas=self._to_int_or_none(self.e_cajas.get()),
            bolsas=self._to_int_or_none(self.e_bolsas.get()),
            ubicacion_destino=self.e_ubicacion.get().strip() or None,
            paqueteria=self.e_paqueteria.get().strip() or None,
            valor_mxn=self.e_valor.get().strip() or None,
            numero_guia=self.e_guia.get().strip() or None,
        )
        self._show_feedback(result)

    def _save_departure(self) -> None:
        result = self.controller.update_departure(
            self.shipment.id,
            horario_entrega=self.e_horario.get().strip() or None,
            nombre_quien_entrega=self.e_quien_entrega.get().strip() or None,
            nombre_chofer_recibe=self.e_chofer.get().strip() or None,
            hora_salida=self.e_hora_salida.get().strip() or None,
            dias_estancia=self._to_int_or_none(self.e_dias_estancia.get()),
        )
        self._show_feedback(result)

    def _attach_pdf(self) -> None:
        path = filedialog.askopenfilename(title="Seleccionar guía PDF", filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        result = self.controller.attach_guide(self.shipment.id, self.shipment.order_number, path)
        if result.ok:
            self.lbl_guia.configure(text=path.split("/")[-1])
        self._show_feedback(result)

    def _show_feedback(self, result) -> None:
        self.feedback.configure(
            text=result.message, text_color="#3ddc84" if result.ok else "#ff5c5c",
        )
        if result.ok:
            self.on_saved()


class ShipmentListView(ctk.CTkFrame):
    def __init__(self, master, controller: ShipmentController, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.controller = controller
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="Embarques",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        self.kpi_row = ctk.CTkFrame(self, fg_color="transparent")
        self.kpi_row.grid(row=1, column=0, sticky="we", pady=(4, 12))

        self.feedback = ctk.CTkLabel(self, text="", text_color="gray60")
        self.feedback.grid(row=2, column=0, sticky="w", pady=(0, 12))

        self.table = ctk.CTkFrame(self, fg_color="transparent")
        self.table.grid(row=3, column=0, sticky="nswe")
        self.table.grid_columnconfigure(0, weight=1)

        self._refresh()

    def _refresh(self) -> None:
        self._refresh_kpis()

        for widget in self.table.winfo_children():
            widget.destroy()

        shipments = self.controller.list_shipments()
        self._shipments_by_id = {s.id: s for s in shipments}

        if not shipments:
            ctk.CTkLabel(
                self.table, text="No hay embarques para mostrar con tu rol actual.",
                text_color="gray60",
            ).grid(row=0, column=0, sticky="w")
            return

        headers = ["OV", "Cliente", "Canal", "Estatus", "Motivo", "Cambiar a", "Detalle"]
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

            ctk.CTkButton(
                self.table, text="Ver / Editar", width=100,
                command=lambda sid=s.id: self._open_detail(sid),
            ).grid(row=row_idx, column=6, sticky="w", padx=8, pady=4)

    def _refresh_kpis(self) -> None:
        for widget in self.kpi_row.winfo_children():
            widget.destroy()

        kpis = self.controller.get_kpis()
        col = 0
        for key, label in _KPI_LABELS.items():
            value = kpis.get(key, 0)
            card = ctk.CTkFrame(self.kpi_row, corner_radius=8)
            card.grid(row=0, column=col, sticky="we", padx=(0, 10))
            ctk.CTkLabel(card, text=label, text_color="gray60", font=ctk.CTkFont(size=11)).pack(
                anchor="w", padx=14, pady=(10, 0)
            )
            ctk.CTkLabel(card, text=str(value), font=ctk.CTkFont(size=20, weight="bold")).pack(
                anchor="w", padx=14, pady=(0, 10)
            )
            col += 1

    def _open_detail(self, shipment_id: int) -> None:
        shipment = self._shipments_by_id[shipment_id]
        ShipmentDetailDialog(self, self.controller, shipment, on_saved=self._refresh)

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
