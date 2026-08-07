"""
Bandeja de notificaciones. Deliberadamente NO es un toast en tiempo real:
se refresca al entrar a la sección, igual que el resto de las vistas del
sistema. Un CEDIS necesita poder consultar qué pasó, no un feed tipo Slack
empujando eventos -- ver decisión registrada en la sesión donde se acordó
esto con el usuario.
"""
from __future__ import annotations
import customtkinter as ctk

from gui.controllers.notification_controller import NotificationController

_AREA_COLOR = {
    "Logística": "#3ddc84",
    "Embarques": "#e0b83d",
}


class NotificationListView(ctk.CTkFrame):
    def __init__(self, master, controller: NotificationController, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.controller = controller
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="we", pady=(0, 12))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header, text="Notificaciones", font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        btn_refresh = ctk.CTkButton(header, text="🔄 Actualizar", width=110, command=self._refresh)
        btn_refresh.grid(row=0, column=1, padx=(0, 8))

        if self.controller.can_clear():
            ctk.CTkButton(
                header, text="🗑️ Vaciar historial", width=140, fg_color="#8a2e2e",
                hover_color="#6e2323", command=self._on_clear,
            ).grid(row=0, column=2)

        self.feedback = ctk.CTkLabel(self, text="", text_color="gray60")
        self.feedback.grid(row=1, column=0, sticky="w", pady=(0, 8))

        self.list_container = ctk.CTkFrame(self, fg_color="transparent")
        self.list_container.grid(row=2, column=0, sticky="nswe")
        self.list_container.grid_columnconfigure(0, weight=1)

        self._refresh()

    def _refresh(self) -> None:
        for widget in self.list_container.winfo_children():
            widget.destroy()

        notifications = self.controller.list_recent()

        if not notifications:
            ctk.CTkLabel(
                self.list_container, text="No hay notificaciones todavía.",
                text_color="gray60",
            ).grid(row=0, column=0, sticky="w")
            return

        for idx, n in enumerate(notifications):
            card = ctk.CTkFrame(self.list_container, corner_radius=8)
            card.grid(row=idx, column=0, sticky="we", pady=(0, 8))
            card.grid_columnconfigure(1, weight=1)

            ctk.CTkFrame(
                card, width=4, fg_color=_AREA_COLOR.get(n.area_origen, "#0284c7"),
            ).grid(row=0, column=0, rowspan=2, sticky="ns", padx=(0, 10))

            top_row = ctk.CTkFrame(card, fg_color="transparent")
            top_row.grid(row=0, column=1, sticky="we", padx=(0, 12), pady=(10, 0))
            top_row.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                top_row, text=n.titulo, font=ctk.CTkFont(weight="bold"), anchor="w",
            ).grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(
                top_row, text=f"{n.area_origen} · {n.timestamp}",
                text_color="gray60", font=ctk.CTkFont(size=11),
            ).grid(row=0, column=1, sticky="e")

            ctk.CTkLabel(
                card, text=n.mensaje, text_color="gray70", anchor="w", justify="left",
                wraplength=700,
            ).grid(row=1, column=1, sticky="w", padx=(0, 12), pady=(2, 10))

    def _on_clear(self) -> None:
        result = self.controller.clear_all()
        self.feedback.configure(
            text=result.message, text_color="#3ddc84" if result.ok else "#ff5c5c",
        )
        self._refresh()
