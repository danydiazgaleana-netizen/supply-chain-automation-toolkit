"""
Shell de la aplicación. Este archivo NO debe crecer con lógica de negocio:
solo arma layout y delega a controllers/. Si encuentras un `db.query(...)`
aquí, es un bug de arquitectura.

Flujo de arranque: LoginView primero, siempre. AppShell (sidebar + contenido)
solo se construye después de un login exitoso vía SessionManager.
"""
from __future__ import annotations
import customtkinter as ctk

from config.settings import settings
from core.session import SessionManager
from gui.controllers.sales_order_controller import SalesOrderController
from gui.controllers.user_management_controller import UserManagementController
from gui.controllers.shipment_controller import ShipmentController
from gui.views.sales_order_form_view import SalesOrderFormView
from gui.views.user_management_view import UserManagementView
from gui.views.shipment_list_view import ShipmentListView
from gui.views.login_view import LoginView

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(settings.app_name)
        self.geometry("1280x800")
        self.minsize(1024, 640)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._current_view: ctk.CTkFrame | None = None
        self._show_login()

    # ---- Navegación entre pantallas raíz ----------------------------------

    def _swap_root_view(self, view: ctk.CTkFrame) -> None:
        if self._current_view is not None:
            self._current_view.destroy()
        self._current_view = view
        view.grid(row=0, column=0, sticky="nswe")

    def _show_login(self) -> None:
        self._swap_root_view(LoginView(self, on_success=self._show_shell))

    def _show_shell(self) -> None:
        self._swap_root_view(AppShell(self, on_logout=self._show_login))


class AppShell(ctk.CTkFrame):
    """Sidebar + área de contenido. Solo existe con sesión activa."""

    def __init__(self, master, on_logout):
        super().__init__(master, fg_color="transparent")
        self.on_logout = on_logout

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_content_area()

    def _build_sidebar(self) -> None:
        session = SessionManager.current()

        sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nswe")
        sidebar.grid_propagate(False)

        ctk.CTkLabel(
            sidebar, text="WMS · Control de\nEmbarques",
            font=ctk.CTkFont(size=18, weight="bold"), justify="left",
        ).pack(padx=20, pady=(24, 16), anchor="w")

        ctk.CTkLabel(
            sidebar, text=f"{session.full_name}\n{session.role.value}",
            justify="left", text_color="gray60", font=ctk.CTkFont(size=12),
        ).pack(padx=20, pady=(0, 20), anchor="w")

        nav_items = ["Órdenes de Venta", "Embarques", "Reportes Ejecutivos", "Usuarios y Roles"]
        for item in nav_items:
            ctk.CTkButton(
                sidebar, text=item, anchor="w", fg_color="transparent",
                hover_color=("gray80", "gray25"), height=40,
                command=lambda i=item: self._navigate(i),
            ).pack(fill="x", padx=12, pady=4)

        ctk.CTkButton(
            sidebar, text="Cerrar sesión", anchor="w", fg_color="transparent",
            hover_color=("gray80", "gray25"), height=40, text_color="#ff5c5c",
            command=self._on_logout,
        ).pack(fill="x", padx=12, pady=(20, 12), side="bottom")

    def _on_logout(self) -> None:
        SessionManager.logout()
        self.on_logout()

    def _build_content_area(self) -> None:
        container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        container.grid(row=0, column=1, sticky="nswe", padx=20, pady=20)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

        self.content = ctk.CTkScrollableFrame(container, fg_color="transparent")
        self.content.grid(row=0, column=0, sticky="nswe")
        self.content.grid_columnconfigure(0, weight=1)

        self._navigate("Órdenes de Venta")

    def _navigate(self, item: str) -> None:
        for widget in self.content.winfo_children():
            widget.destroy()

        session = SessionManager.current()

        if item == "Órdenes de Venta":
            controller = SalesOrderController(
                current_user_role=session.role, current_user_id=session.user_id,
            )
            SalesOrderFormView(self.content, controller=controller).grid(
                row=0, column=0, sticky="nswe", pady=10
            )
        elif item == "Embarques":
            controller = ShipmentController(session=session)
            ShipmentListView(self.content, controller=controller).grid(
                row=0, column=0, sticky="nswe", pady=10
            )
        elif item == "Usuarios y Roles":
            controller = UserManagementController(session=session)
            UserManagementView(self.content, controller=controller).grid(
                row=0, column=0, sticky="nswe", pady=10
            )
        else:
            ctk.CTkLabel(
                self.content, text=f"'{item}' todavía no está implementado.",
                text_color="gray60",
            ).grid(row=0, column=0, sticky="w", pady=10)


if __name__ == "__main__":
    from infrastructure.db.session import init_db
    init_db()
    app = MainWindow()
    app.mainloop()