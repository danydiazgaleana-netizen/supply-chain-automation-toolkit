"""
Vista de Captura Logística. Incluye:
- Formulario de alta de OV (con número de pedido, cajas declaradas, agente
  de ventas, guía PDF).
- Lista filtrable de OVs ya capturadas, para que Logística pueda buscar un
  pedido sin tener que recordarlo de memoria (petición de la directiva del
  CEDIS y del encargado de Embarques).
"""
from __future__ import annotations
from tkinter import filedialog
import customtkinter as ctk

from gui.controllers.sales_order_controller import SalesOrderController


class LogisticaFormView(ctk.CTkFrame):
    def __init__(self, master, controller: SalesOrderController, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.controller = controller
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            self, text="Captura Logística", font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 12))

        self._build_form()
        self._build_search_list()
        self._refresh_list()

    # ---- Formulario de captura -------------------------------------

    def _build_form(self) -> None:
        form = ctk.CTkFrame(self)
        form.grid(row=1, column=0, sticky="we", pady=(0, 16))
        form.grid_columnconfigure(1, weight=1)
        form.grid_columnconfigure(3, weight=1)

        self._archivo_pdf_temp = ""

        r = 0
        ctk.CTkLabel(form, text="OV").grid(row=r, column=0, sticky="w", padx=(16, 8), pady=(16, 4))
        self.entry_ov = ctk.CTkEntry(form, placeholder_text="Ej. 4090")
        self.entry_ov.grid(row=r, column=1, sticky="we", padx=(0, 16), pady=(16, 4))

        ctk.CTkLabel(form, text="Cliente").grid(row=r, column=2, sticky="w", padx=(0, 8), pady=(16, 4))
        self.entry_cliente = ctk.CTkEntry(form, placeholder_text="Nombre del cliente")
        self.entry_cliente.grid(row=r, column=3, sticky="we", padx=(0, 16), pady=(16, 4))

        r += 1
        ctk.CTkLabel(form, text="Canal").grid(row=r, column=0, sticky="w", padx=(16, 8), pady=4)
        channel_codes = self.controller.list_active_channel_codes()
        self.channel_var = ctk.StringVar(value=channel_codes[0] if channel_codes else "")
        ctk.CTkOptionMenu(
            form, values=channel_codes or ["(sin canales)"], variable=self.channel_var,
        ).grid(row=r, column=1, sticky="we", padx=(0, 16), pady=4)

        ctk.CTkLabel(form, text="Agente de ventas").grid(row=r, column=2, sticky="w", padx=(0, 8), pady=4)
        self.entry_agente = ctk.CTkEntry(form, placeholder_text="Quién confirmó el pedido")
        self.entry_agente.grid(row=r, column=3, sticky="we", padx=(0, 16), pady=4)

        r += 1
        ctk.CTkLabel(form, text="Número de pedido").grid(row=r, column=0, sticky="w", padx=(16, 8), pady=4)
        self.entry_pedido = ctk.CTkEntry(form, placeholder_text="Ej. GLS2026-133-1036")
        self.entry_pedido.grid(row=r, column=1, sticky="we", padx=(0, 16), pady=4)

        ctk.CTkLabel(form, text="Cajas declaradas").grid(row=r, column=2, sticky="w", padx=(0, 8), pady=4)
        self.entry_cajas = ctk.CTkEntry(form, placeholder_text="0")
        self.entry_cajas.grid(row=r, column=3, sticky="we", padx=(0, 16), pady=4)

        r += 1
        guia_row = ctk.CTkFrame(form, fg_color="transparent")
        guia_row.grid(row=r, column=0, columnspan=4, sticky="we", padx=16, pady=(8, 4))
        ctk.CTkButton(guia_row, text="Adjuntar guía PDF", width=160, command=self._seleccionar_pdf).pack(side="left")
        self.lbl_pdf = ctk.CTkLabel(guia_row, text="Ningún archivo seleccionado", text_color="gray60")
        self.lbl_pdf.pack(side="left", padx=10)

        r += 1
        self.feedback = ctk.CTkLabel(form, text="", text_color="gray60")
        self.feedback.grid(row=r, column=0, columnspan=4, sticky="w", padx=16, pady=(4, 0))

        r += 1
        ctk.CTkButton(
            form, text="Guardar captura logística", command=self._guardar,
        ).grid(row=r, column=0, columnspan=4, sticky="we", padx=16, pady=(8, 16))

    def _seleccionar_pdf(self) -> None:
        path = filedialog.askopenfilename(title="Seleccionar guía PDF", filetypes=[("PDF", "*.pdf")])
        if path:
            self._archivo_pdf_temp = path
            self.lbl_pdf.configure(text=path.split("/")[-1].split("\\")[-1], text_color="#3ddc84")

    def _guardar(self) -> None:
        result = self.controller.create_order(
            order_number=self.entry_ov.get().strip(),
            customer_name=self.entry_cliente.get().strip(),
            channel=self.channel_var.get(),
            cajas=self.entry_cajas.get().strip(),
            numero_pedido_logistica=self.entry_pedido.get().strip(),
            agente_ventas=self.entry_agente.get().strip(),
            archivo_guia_path=self._archivo_pdf_temp,
        )
        self.feedback.configure(text=result.message, text_color="#3ddc84" if result.ok else "#ff5c5c")
        if result.ok:
            for entry in (self.entry_ov, self.entry_cliente, self.entry_agente, self.entry_pedido, self.entry_cajas):
                entry.delete(0, "end")
            self._archivo_pdf_temp = ""
            self.lbl_pdf.configure(text="Ningún archivo seleccionado", text_color="gray60")
            self._refresh_list()

    # ---- Lista filtrable de pedidos ya capturados -----------------

    def _build_search_list(self) -> None:
        # Fila propia para el buscador, debajo del form (row=1 ya la usa el
        # form -- el buscador y la lista van en la row=2/3, con weight=1 en
        # la fila 3 para que la tabla pueda crecer).
        search_row = ctk.CTkFrame(self, fg_color="transparent")
        search_row.grid(row=2, column=0, sticky="we", pady=(0, 8))
        search_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(search_row, text="Pedidos capturados", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, sticky="w"
        )
        self.entry_buscar = ctk.CTkEntry(search_row, placeholder_text="Buscar por OV, cliente o número de pedido...", width=320)
        self.entry_buscar.grid(row=0, column=1, sticky="e", padx=(8, 0))
        self.entry_buscar.bind("<KeyRelease>", lambda _e: self._refresh_list())

        self.list_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list_container.grid(row=3, column=0, sticky="nswe")
        self.list_container.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

    def _refresh_list(self) -> None:
        for widget in self.list_container.winfo_children():
            widget.destroy()

        texto = self.entry_buscar.get() if hasattr(self, "entry_buscar") else ""
        orders = self.controller.search_orders(texto)

        if not orders:
            ctk.CTkLabel(self.list_container, text="No hay pedidos capturados.", text_color="gray60").grid(
                row=0, column=0, sticky="w"
            )
            return

        headers = ["OV", "Cliente", "Canal", "Agente de ventas", "N° Pedido", "Cajas"]
        for col, text in enumerate(headers):
            ctk.CTkLabel(
                self.list_container, text=text, font=ctk.CTkFont(weight="bold"), text_color="gray60",
            ).grid(row=0, column=col, sticky="w", padx=8, pady=(0, 6))

        for row_idx, o in enumerate(orders, start=1):
            ctk.CTkLabel(self.list_container, text=o.order_number).grid(row=row_idx, column=0, sticky="w", padx=8, pady=3)
            ctk.CTkLabel(self.list_container, text=o.customer_name).grid(row=row_idx, column=1, sticky="w", padx=8, pady=3)
            ctk.CTkLabel(self.list_container, text=o.channel).grid(row=row_idx, column=2, sticky="w", padx=8, pady=3)
            ctk.CTkLabel(self.list_container, text=o.agente_ventas or "—").grid(row=row_idx, column=3, sticky="w", padx=8, pady=3)
            ctk.CTkLabel(self.list_container, text=o.numero_pedido_logistica or "—").grid(row=row_idx, column=4, sticky="w", padx=8, pady=3)
            ctk.CTkLabel(self.list_container, text=str(o.total_cajas_logistica) if o.total_cajas_logistica is not None else "—").grid(
                row=row_idx, column=5, sticky="w", padx=8, pady=3
            )
