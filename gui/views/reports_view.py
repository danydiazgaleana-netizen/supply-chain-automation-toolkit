"""
Vista de Reportes Ejecutivos. Los canales disponibles para exportar por
separado se leen de la tabla `channels` vía SalesOrderController (mismo
patrón que el dropdown de captura de OV) -- no una lista hardcodeada.
"""
from __future__ import annotations
from datetime import datetime
from tkinter import filedialog
import customtkinter as ctk

from gui.controllers.report_controller import ReportController
from gui.controllers.sales_order_controller import SalesOrderController
from core.session import SessionState


class ReportsView(ctk.CTkFrame):
    def __init__(self, master, session: SessionState, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.controller = ReportController(session)
        self._channel_source = SalesOrderController(
            current_user_role=session.role, current_user_id=session.user_id,
        )
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="Reportes Ejecutivos",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        ctk.CTkLabel(
            self, text="El reporte respeta lo que tu rol puede ver: si eres OPERADOR, "
                       "solo exporta los embarques que tú capturaste.",
            text_color="gray60", wraplength=600, justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(0, 16))

        consolidated_card = ctk.CTkFrame(self)
        consolidated_card.grid(row=2, column=0, sticky="we", pady=(0, 16))
        consolidated_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            consolidated_card, text="Consolidado general",
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 4))
        ctk.CTkLabel(
            consolidated_card, text="Todos los canales en una sola hoja.",
            text_color="gray60",
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))
        ctk.CTkButton(
            consolidated_card, text="📊 Exportar consolidado a Excel",
            command=self._export_consolidated,
        ).grid(row=2, column=0, sticky="w", padx=16, pady=(0, 16))

        channel_card = ctk.CTkFrame(self)
        channel_card.grid(row=3, column=0, sticky="we")
        channel_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            channel_card, text="Por canal individual",
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=16, pady=(16, 12))

        channel_codes = self._channel_source.list_active_channel_codes()
        self.channel_var = ctk.StringVar(value=channel_codes[0] if channel_codes else "")
        ctk.CTkOptionMenu(
            channel_card, values=channel_codes or ["(sin canales)"], variable=self.channel_var,
        ).grid(row=1, column=0, sticky="w", padx=(16, 8), pady=(0, 16))
        ctk.CTkButton(
            channel_card, text="📊 Exportar canal a Excel", command=self._export_channel,
        ).grid(row=1, column=1, sticky="w", pady=(0, 16))

        self.feedback = ctk.CTkLabel(self, text="", text_color="gray60", wraplength=700, justify="left")
        self.feedback.grid(row=4, column=0, sticky="w", pady=(16, 0))

    def _default_filename(self, suffix: str) -> str:
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        return f"reporte_{suffix}_{stamp}.xlsx"

    def _export_consolidated(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
            initialfile=self._default_filename("consolidado"),
        )
        if not path:
            return
        result = self.controller.export_consolidated(path)
        self._show(result)

    def _export_channel(self) -> None:
        channel = self.channel_var.get()
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
            initialfile=self._default_filename(channel.lower()),
        )
        if not path:
            return
        result = self.controller.export_channel(channel, path)
        self._show(result)

    def _show(self, result) -> None:
        self.feedback.configure(
            text=result.message, text_color="#3ddc84" if result.ok else "#ff5c5c",
        )
