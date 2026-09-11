"""
Vista de Discrepancias - Muestra OV donde Logística y Embarques no coinciden.
"""
from __future__ import annotations
import customtkinter as ctk
from tkinter import ttk

from gui.controllers.shipment_controller import ShipmentController

COLORS = {
    "danger": "#ff1744",
    "success": "#00c853",
    "warning": "#ffab00",
    "text_secondary": "#8899bb",
}


class DiscrepanciasView(ctk.CTkFrame):
    def __init__(self, master, controller: ShipmentController, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.controller = controller
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(
            header, text="🚨 Detección de Discrepancias",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            header, text="🔄 Actualizar", width=120,
            command=self._refresh, fg_color="#334155"
        ).pack(side="right", padx=5)

        self.feedback = ctk.CTkLabel(self, text="", text_color="gray60")
        self.feedback.grid(row=1, column=0, sticky="w", pady=(0, 10))

        self.table_container = ctk.CTkFrame(self, fg_color="transparent")
        self.table_container.grid(row=2, column=0, sticky="nswe")
        self.table_container.grid_columnconfigure(0, weight=1)
        self.table_container.grid_rowconfigure(0, weight=1)

        self.tree = None
        self._refresh()

    def _refresh(self):
        for widget in self.table_container.winfo_children():
            widget.destroy()

        try:
            discrepancias = self.controller.list_discrepancias()
        except Exception as e:
            ctk.CTkLabel(
                self.table_container, text=f"❌ Error al cargar discrepancias: {e}",
                text_color="#ff5c5c"
            ).grid(row=0, column=0, sticky="w")
            return

        if not discrepancias:
            ctk.CTkLabel(
                self.table_container, text="✅ No hay discrepancias. Todas las OV están conciliadas.",
                text_color=COLORS["success"], font=ctk.CTkFont(size=14, weight="bold")
            ).grid(row=0, column=0, sticky="w", pady=20)
            return

        frame = ctk.CTkFrame(self.table_container, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nswe")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        columns = ("OV", "Cliente", "Logística", "Embarques", "Diferencia", "Estatus")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=12)

        col_widths = {"OV": 80, "Cliente": 120, "Logística": 260, "Embarques": 260, "Diferencia": 80, "Estatus": 160}
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=col_widths.get(col, 100), anchor="w")

        scroll_y = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        scroll_x = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Alerta.Treeview", background="#ffcccc", foreground="#000000", font=("Segoe UI", 10, "bold"))

        # Cualquier discrepancia sin resolver bloquea despacho -- no es un
        # caso especial de una OV en particular, es la regla general que
        # ya se aplica en ShipmentService.change_status().
        for disc in discrepancias:
            ov = disc.get("ov", "")
            cliente = disc.get("cliente", "N/A")
            logistica = f"Pedido: {disc.get('numero_pedido_logistica', 'N/A')} ({disc.get('valor_logistica', 0)} cajas)"
            embarques = f"Pedido: {disc.get('numero_pedido_embarque', 'N/A')} ({disc.get('valor_embarques', 0)} cajas)"
            diferencia = disc.get("diferencia", 0)

            self.tree.insert("", "end", values=(
                ov, cliente, logistica, embarques, diferencia, "🔴 Despacho bloqueado"
            ), tags=("alerta",))

        self.tree.tag_configure("alerta", background="#ffcccc", foreground="#000000", font=("Segoe UI", 10, "bold"))

        self.feedback.configure(
            text=f"🔍 Se encontraron {len(discrepancias)} discrepancias con despacho bloqueado.",
            text_color=COLORS["danger"],
        )
