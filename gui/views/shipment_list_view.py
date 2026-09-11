"""
Vista de Embarques -- muestra estatus, badge de discrepancia, y abre
PedidoDialog para que Embarques capture/corrija su parte del pedido.
Organizada en pestañas por canal (VL, PEGE, AMAZON, etc.) para que los
pedidos de distintos canales no se mezclen en una sola tabla larga
(petición de la directiva del CEDIS y del encargado de Embarques).
"""
from __future__ import annotations
import customtkinter as ctk

from config.settings import settings
from core.models.entities import ShipmentStatus
from gui.controllers.shipment_controller import ShipmentController
from gui.views.pedido_dialog import PedidoDialog

_COLOR_HEX = {"VERDE": "#3ddc84", "AMARILLO": "#e0b83d", "ROJO": "#ff5c5c"}
_TAB_TODOS = "Todos"


class ShipmentListView(ctk.CTkFrame):
    def __init__(self, master, controller: ShipmentController, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.controller = controller
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            self, text="Embarques", font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        self.feedback = ctk.CTkLabel(self, text="", text_color="gray60", wraplength=900, justify="left")
        self.feedback.grid(row=1, column=0, sticky="w", pady=(0, 12))

        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=2, column=0, sticky="nswe")
        self._tab_tables: dict[str, ctk.CTkFrame] = {}

        self._refresh()

    def _refresh(self) -> None:
        shipments = self.controller.list_shipments()
        self._shipments_by_id = {s.id: s for s in shipments}

        discrepancias = self.controller.list_discrepancias()
        ov_con_discrepancia = {d["ov"] for d in discrepancias}

        canales_presentes = sorted({s.channel for s in shipments})
        tabs_necesarias = [_TAB_TODOS] + canales_presentes

        # CTkTabview no permite quitar pestañas dinámicamente sin reconstruir
        # -- si cambió el set de canales, se reconstruye el tabview completo.
        if set(self._tab_tables.keys()) != set(tabs_necesarias):
            for tab_name in list(self._tab_tables.keys()):
                pass  # el propio destroy() del tabview de abajo limpia todo
            self.tabview.destroy()
            self.tabview = ctk.CTkTabview(self)
            self.tabview.grid(row=2, column=0, sticky="nswe")
            self._tab_tables = {}
            for tab_name in tabs_necesarias:
                self.tabview.add(tab_name)
                table = ctk.CTkScrollableFrame(self.tabview.tab(tab_name), fg_color="transparent")
                table.pack(fill="both", expand=True)
                table.grid_columnconfigure(0, weight=1)
                self._tab_tables[tab_name] = table

        for tab_name, table in self._tab_tables.items():
            filtered = shipments if tab_name == _TAB_TODOS else [s for s in shipments if s.channel == tab_name]
            self._render_table(table, filtered, ov_con_discrepancia)

    def _render_table(self, table: ctk.CTkFrame, shipments: list, ov_con_discrepancia: set) -> None:
        for widget in table.winfo_children():
            widget.destroy()

        if not shipments:
            ctk.CTkLabel(
                table, text="No hay embarques para mostrar con tu rol actual.", text_color="gray60",
            ).grid(row=0, column=0, sticky="w")
            return

        headers = [
            "OV", "Cliente", "Canal", "Estatus", "Pedido Embarques", "Cajas",
            "Tiempo en Embarques", "Conciliacion", "Cambiar a", "Editar",
        ]
        for col, text in enumerate(headers):
            ctk.CTkLabel(
                table, text=text, font=ctk.CTkFont(weight="bold"), text_color="gray60",
            ).grid(row=0, column=col, sticky="w", padx=8, pady=(0, 8))

        for row_idx, s in enumerate(shipments, start=1):
            ctk.CTkLabel(table, text=s.order_number).grid(row=row_idx, column=0, sticky="w", padx=8, pady=4)
            ctk.CTkLabel(table, text=s.customer_name).grid(row=row_idx, column=1, sticky="w", padx=8, pady=4)
            ctk.CTkLabel(table, text=s.channel).grid(row=row_idx, column=2, sticky="w", padx=8, pady=4)

            ctk.CTkLabel(
                table, text="* " + s.status, text_color=_COLOR_HEX.get(s.status_color, "#FFFFFF"),
            ).grid(row=row_idx, column=3, sticky="w", padx=8, pady=4)

            ctk.CTkLabel(table, text=s.numero_pedido_embarque or "-").grid(row=row_idx, column=4, sticky="w", padx=8, pady=4)
            ctk.CTkLabel(table, text=str(s.cajas_embarque) if s.cajas_embarque is not None else "-").grid(
                row=row_idx, column=5, sticky="w", padx=8, pady=4
            )

            ctk.CTkLabel(table, text=s.tiempo_en_embarques, text_color="gray70").grid(
                row=row_idx, column=6, sticky="w", padx=8, pady=4
            )

            if s.order_number in ov_con_discrepancia:
                ctk.CTkLabel(table, text="Discrepancia", text_color="#ff5c5c").grid(
                    row=row_idx, column=7, sticky="w", padx=8, pady=4
                )
            else:
                ctk.CTkLabel(table, text="Conciliado", text_color="#3ddc84").grid(
                    row=row_idx, column=7, sticky="w", padx=8, pady=4
                )

            allowed = settings.STATUS_TRANSITIONS.get(s.status, ())
            if allowed:
                var = ctk.StringVar(value="Seleccionar...")
                ctk.CTkOptionMenu(
                    table, values=list(allowed), variable=var, width=140,
                    command=lambda new_status, sid=s.id, ver=s.version: self._on_status_pick(sid, new_status, ver),
                ).grid(row=row_idx, column=8, sticky="w", padx=8, pady=4)
            else:
                ctk.CTkLabel(table, text="(final)", text_color="gray50").grid(row=row_idx, column=8, sticky="w", padx=8, pady=4)

            ctk.CTkButton(
                table, text="Editar", width=80, command=lambda sid=s.id: self._open_dialog(sid),
            ).grid(row=row_idx, column=9, sticky="w", padx=8, pady=4)

    def _open_dialog(self, shipment_id: int) -> None:
        shipment_dto = self._shipments_by_id[shipment_id]
        dialog = PedidoDialog(
            self,
            on_confirm=self.controller.update_shipment_detalles,
            on_attach_guide=self.controller.attach_guide,
            on_download_guide=self.controller.download_guide,
            shipment_dto=shipment_dto,
            numero_pedido_logistica=shipment_dto.numero_pedido_logistica,
            shipment_id=shipment_id,
        )
        self.wait_window(dialog)
        self._refresh()

    def _on_status_pick(self, shipment_id: int, new_status_str: str, version: int) -> None:
        result = self.controller.change_status(shipment_id, ShipmentStatus(new_status_str), version_expected=version)
        self.feedback.configure(text=result.message, text_color="#3ddc84" if result.ok else "#ff5c5c")
        self._refresh()
