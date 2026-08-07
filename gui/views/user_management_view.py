"""
Vista de gestión de usuarios. Solo se monta si el rol tiene permiso
gestionar_usuarios — pero igual valida en cada acción vía el controller,
porque una vista oculta en el sidebar no es control de acceso real.
"""
from __future__ import annotations
import customtkinter as ctk

from core.models.entities import UserRole
from gui.controllers.user_management_controller import UserManagementController


class UserManagementView(ctk.CTkFrame):
    def __init__(self, master, controller: UserManagementController, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.controller = controller
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="Usuarios y Roles",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 16))

        self._build_create_form()

        self.create_feedback = ctk.CTkLabel(self, text="", text_color="gray60")
        self.create_feedback.grid(row=2, column=0, sticky="w", pady=(0, 8))

        self.table_container = ctk.CTkFrame(self, fg_color="transparent")
        self.table_container.grid(row=3, column=0, sticky="nswe", pady=(4, 0))
        self.table_container.grid_columnconfigure(0, weight=1)

        self._refresh_table()

    # ---- Alta de usuario ----------------------------------------------

    def _build_create_form(self) -> None:
        form = ctk.CTkFrame(self)
        form.grid(row=1, column=0, sticky="we", pady=(0, 20))
        for col in range(5):
            form.grid_columnconfigure(col, weight=1 if col < 4 else 0)

        self.entry_username = ctk.CTkEntry(form, placeholder_text="Usuario")
        self.entry_username.grid(row=0, column=0, sticky="we", padx=(16, 6), pady=16)

        self.entry_fullname = ctk.CTkEntry(form, placeholder_text="Nombre completo")
        self.entry_fullname.grid(row=0, column=1, sticky="we", padx=6, pady=16)

        self.entry_password = ctk.CTkEntry(form, placeholder_text="Password (min. 8)", show="•")
        self.entry_password.grid(row=0, column=2, sticky="we", padx=6, pady=16)

        self.role_var = ctk.StringVar(value=UserRole.OPERADOR.value)
        ctk.CTkOptionMenu(
            form, values=[r.value for r in UserRole], variable=self.role_var,
        ).grid(row=0, column=3, sticky="we", padx=6, pady=16)

        ctk.CTkButton(form, text="Crear", width=90, command=self._on_create).grid(
            row=0, column=4, sticky="we", padx=(6, 16), pady=16
        )

    def _on_create(self) -> None:
        result = self.controller.create_user(
            username=self.entry_username.get(),
            password=self.entry_password.get(),
            full_name=self.entry_fullname.get(),
            role=UserRole(self.role_var.get()),
        )
        self.create_feedback.configure(
            text=result.message, text_color="#3ddc84" if result.ok else "#ff5c5c",
        )
        if result.ok:
            self.entry_username.delete(0, "end")
            self.entry_fullname.delete(0, "end")
            self.entry_password.delete(0, "end")
            self._refresh_table()

    # ---- Tabla de usuarios ----------------------------------------------

    def _refresh_table(self) -> None:
        for widget in self.table_container.winfo_children():
            widget.destroy()

        users, err = self.controller.list_users()
        if err:
            ctk.CTkLabel(self.table_container, text=err, text_color="#ff5c5c").grid(
                row=0, column=0, sticky="w"
            )
            return

        headers = ["Usuario", "Nombre", "Rol", "Activo", "Acciones"]
        for col, text in enumerate(headers):
            ctk.CTkLabel(
                self.table_container, text=text, font=ctk.CTkFont(weight="bold"),
                text_color="gray60",
            ).grid(row=0, column=col, sticky="w", padx=8, pady=(0, 8))

        for row_idx, user in enumerate(users, start=1):
            ctk.CTkLabel(self.table_container, text=user.username).grid(
                row=row_idx, column=0, sticky="w", padx=8, pady=4
            )
            ctk.CTkLabel(self.table_container, text=user.full_name).grid(
                row=row_idx, column=1, sticky="w", padx=8, pady=4
            )

            role_var = ctk.StringVar(value=user.role)
            ctk.CTkOptionMenu(
                self.table_container, values=[r.value for r in UserRole], variable=role_var,
                width=140,
                command=lambda new_role, uid=user.id: self._on_role_change(uid, new_role),
            ).grid(row=row_idx, column=2, sticky="w", padx=8, pady=4)

            ctk.CTkLabel(
                self.table_container, text="Sí" if user.is_active else "No",
                text_color="#3ddc84" if user.is_active else "#ff5c5c",
            ).grid(row=row_idx, column=3, sticky="w", padx=8, pady=4)

            toggle_text = "Desactivar" if user.is_active else "Activar"
            ctk.CTkButton(
                self.table_container, text=toggle_text, width=100,
                fg_color="#8a2e2e" if user.is_active else "#2e6b3e",
                hover_color="#6e2323" if user.is_active else "#255530",
                command=lambda uid=user.id, active=user.is_active: self._on_toggle_active(uid, not active),
            ).grid(row=row_idx, column=4, sticky="w", padx=8, pady=4)

    def _on_role_change(self, user_id: int, new_role: str) -> None:
        result = self.controller.change_role(user_id, UserRole(new_role))
        self.create_feedback.configure(
            text=result.message, text_color="#3ddc84" if result.ok else "#ff5c5c",
        )
        self._refresh_table()  # revierte visualmente si el cambio fue rechazado

    def _on_toggle_active(self, user_id: int, new_state: bool) -> None:
        result = self.controller.toggle_active(user_id, new_state)
        self.create_feedback.configure(
            text=result.message, text_color="#3ddc84" if result.ok else "#ff5c5c",
        )
        self._refresh_table()
