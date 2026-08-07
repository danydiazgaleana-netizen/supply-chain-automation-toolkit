from __future__ import annotations
from dataclasses import dataclass

from infrastructure.db.session import get_session
from core.services.auth_service import AuthService, AuthenticationError
from core.session import SessionManager, SessionState


@dataclass
class LoginResult:
    ok: bool
    message: str


class LoginController:
    def attempt_login(self, username: str, password: str) -> LoginResult:
        if not username.strip() or not password:
            return LoginResult(False, "Ingresa usuario y contraseña.")

        try:
            with get_session() as db:
                auth = AuthService(db)
                user = auth.authenticate(username.strip(), password)
                SessionManager.login(SessionState(
                    user_id=user.id, username=user.username,
                    full_name=user.full_name, role=user.role,
                ))
                return LoginResult(True, f"Bienvenido, {user.full_name}.")
        except AuthenticationError as exc:
            return LoginResult(False, str(exc))
        except Exception as exc:  # noqa: BLE001 — frontera GUI
            return LoginResult(False, f"Error inesperado: {exc}")
