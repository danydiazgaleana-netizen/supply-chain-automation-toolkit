"""
Vista de captura de Orden de Venta. Solo construye UI y delega al controller.
Cero lógica de negocio aquí — si ves una validación de reglas de negocio en
este archivo (más allá de "está vacío el campo"), está en el lugar equivocado.
"""
from __future__ import annotations
import customtkinter as ctk

from gui.controllers.sales_order_controller import SalesOrderController


class SalesOrderFormView(ctk.CTkFrame):
    def __init__(self, master, controller: SalesOrderController, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.controller = controller
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="Nueva Orden de Venta",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 16))

        form = ctk.CTkFrame(self)
        form.grid(row=1, column=0, sticky="nswe")
        form.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(form, text="Número de OV").grid(row=0, column=0, sticky="w", padx=16, pady=(16, 4))
        self.entry_order_number = ctk.CTkEntry(form, placeholder_text="Ej. OV-2026-00123")
        self.entry_order_number.grid(row=1, column=0, columnspan=2, sticky="we", padx=16, pady=(0, 12))

        ctk.CTkLabel(form, text="Cliente").grid(row=2, column=0, sticky="w", padx=16, pady=(0, 4))
        self.entry_customer = ctk.CTkEntry(form, placeholder_text="Razón social del cliente")
        self.entry_customer.grid(row=3, column=0, columnspan=2, sticky="we", padx=16, pady=(0, 12))

        ctk.CTkLabel(form, text="Canal logístico").grid(row=4, column=0, sticky="w", padx=16, pady=(0, 4))
        channel_codes = self.controller.list_active_channel_codes()
        self.channel_var = ctk.StringVar(value=channel_codes[0] if channel_codes else "")
        self.dropdown_channel = ctk.CTkOptionMenu(
            form, values=channel_codes or ["(sin canales — correr seed_channels)"],
            variable=self.channel_var,
        )
        self.dropdown_channel.grid(row=5, column=0, columnspan=2, sticky="we", padx=16, pady=(0, 16))

        self.feedback_label = ctk.CTkLabel(form, text="", text_color="gray60")
        self.feedback_label.grid(row=6, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 8))

        ctk.CTkButton(
            form, text="Guardar OV", command=self._on_submit,
        ).grid(row=7, column=0, columnspan=2, sticky="we", padx=16, pady=(0, 16))

    def _on_submit(self) -> None:
        result = self.controller.create_order(
            order_number=self.entry_order_number.get(),
            customer_name=self.entry_customer.get(),
            channel=self.channel_var.get(),
        )
        self.feedback_label.configure(
            text=result.message,
            text_color="#3ddc84" if result.ok else "#ff5c5c",
        )
        if result.ok:
            self.entry_order_number.delete(0, "end")
            self.entry_customer.delete(0, "end")
