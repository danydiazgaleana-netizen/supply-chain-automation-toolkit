from __future__ import annotations
from dataclasses import dataclass

from config.settings import settings
from infrastructure.db.session import get_session
from core.services.auth_service import (
    AuthService, UserAlreadyExistsError, SelfLockoutError,
)
from core.models.entities import UserRole
from core.schemas.dto import UserDTO, user_to_dto
from core.session import SessionState


@dataclass
class OpResult:
    ok: bool
    message: str


class UserManagementController:
    def __init__(self, session: SessionState):
        self.session = session

    def _require_permission(self) -> OpResult | None:
        if not settings.ROLE_PERMISSIONS[self.session.role.value]["gestionar_usuarios"]:
            return OpResult(False, "Tu rol no tiene permiso para gestionar usuarios.")
        return None

    def list_users(self) -> tuple[list[UserDTO], str | None]:
        denied = self._require_permission()
        if denied:
            return [], denied.message
        with get_session() as db:
            auth = AuthService(db)
            users = [user_to_dto(u) for u in auth.list_users()]
        return users, None

    def create_user(self, username: str, password: str, full_name: str, role: UserRole) -> OpResult:
        denied = self._require_permission()
        if denied:
            return denied
        try:
            with get_session() as db:
                auth = AuthService(db)
                user = auth.create_user(
                    username=username.strip(), plain_password=password,
                    full_name=full_name.strip(), role=role,
                    created_by_admin_id=self.session.user_id,
                )
                return OpResult(True, f"Usuario '{user.username}' creado.")
        except (UserAlreadyExistsError, ValueError) as exc:
            return OpResult(False, str(exc))

    def toggle_active(self, target_user_id: int, is_active: bool) -> OpResult:
        denied = self._require_permission()
        if denied:
            return denied
        try:
            with get_session() as db:
                auth = AuthService(db)
                user = auth.set_active(target_user_id, is_active, self.session.user_id)
                estado = "activado" if is_active else "desactivado"
                return OpResult(True, f"Usuario '{user.username}' {estado}.")
        except SelfLockoutError as exc:
            return OpResult(False, str(exc))
        except ValueError as exc:
            return OpResult(False, str(exc))

    def change_role(self, target_user_id: int, new_role: UserRole) -> OpResult:
        denied = self._require_permission()
        if denied:
            return denied
        try:
            with get_session() as db:
                auth = AuthService(db)
                user = auth.change_role(target_user_id, new_role, self.session.user_id)
                return OpResult(True, f"Rol de '{user.username}' actualizado a {new_role.value}.")
        except SelfLockoutError as exc:
            return OpResult(False, str(exc))
        except ValueError as exc:
            return OpResult(False, str(exc))
