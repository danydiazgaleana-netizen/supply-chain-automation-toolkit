from __future__ import annotations
from typing import Callable
import customtkinter as ctk

from gui.controllers.login_controller import LoginController


class LoginView(ctk.CTkFrame):
    def __init__(self, master, on_success: Callable[[], None], **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.controller = LoginController()
        self.on_success = on_success

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        card = ctk.CTkFrame(self, width=360)
        card.grid(row=0, column=0)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text="WMS · Control de Embarques",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, padx=32, pady=(32, 4))
        ctk.CTkLabel(
            card, text="Inicia sesión para continuar",
            text_color="gray60",
        ).grid(row=1, column=0, padx=32, pady=(0, 20))

        self.entry_user = ctk.CTkEntry(card, placeholder_text="Usuario", width=280)
        self.entry_user.grid(row=2, column=0, padx=32, pady=6)

        self.entry_pass = ctk.CTkEntry(card, placeholder_text="Contraseña", show="•", width=280)
        self.entry_pass.grid(row=3, column=0, padx=32, pady=6)
        self.entry_pass.bind("<Return>", lambda _e: self._on_submit())

        self.feedback = ctk.CTkLabel(card, text="", text_color="#ff5c5c")
        self.feedback.grid(row=4, column=0, padx=32, pady=(6, 4))

        ctk.CTkButton(
            card, text="Iniciar sesión", width=280, command=self._on_submit,
        ).grid(row=5, column=0, padx=32, pady=(10, 32))

    def _on_submit(self) -> None:
        result = self.controller.attempt_login(self.entry_user.get(), self.entry_pass.get())
        if result.ok:
            self.on_success()
        else:
            self.feedback.configure(text=result.message)
            self.entry_pass.delete(0, "end")
