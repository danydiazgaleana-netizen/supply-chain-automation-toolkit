"""
Autenticación. Reglas duras:
- Contraseñas NUNCA en texto plano, ni en memoria más tiempo del necesario.
- bcrypt, no MD5/SHA1 (ambos son inaceptables para passwords, sin excepción).
- Login fallido también se audita — un intento fallido repetido es una señal
  de seguridad, no un detalle a ignorar.
"""
from __future__ import annotations
from typing import Optional

import bcrypt
from sqlalchemy.orm import Session

from core.models.entities import User, UserRole
from infrastructure.logging.audit_service import AuditService


class AuthenticationError(Exception):
    pass


class UserAlreadyExistsError(Exception):
    pass


class SelfLockoutError(Exception):
    """Un ADMIN no puede desactivarse ni quitarse el rol ADMIN a sí mismo:
    dejaría al sistema sin nadie capaz de gestionar usuarios."""
    pass


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))


class AuthService:
    def __init__(self, db: Session):
        self._db = db
        self._audit = AuditService(db)

    def create_user(
        self, username: str, plain_password: str, full_name: str, role: UserRole,
        created_by_admin_id: Optional[int] = None,
    ) -> User:
        existing = self._db.query(User).filter(User.username == username).first()
        if existing is not None:
            raise UserAlreadyExistsError(f"El usuario '{username}' ya existe.")

        if len(plain_password) < 8:
            # Regla mínima de higiene. No es exhaustiva (no valida complejidad),
            # pero bloquea el caso más común de contraseña trivial en un demo.
            raise ValueError("La contraseña debe tener al menos 8 caracteres.")

        user = User(
            username=username,
            password_hash=hash_password(plain_password),
            full_name=full_name,
            role=role,
        )
        self._db.add(user)
        self._db.flush()
        self._audit.log(
            "USER_CREATED", f"User:{user.id}", detail=f"{username} ({role.value})",
            user_id=created_by_admin_id,
        )
        return user

    def authenticate(self, username: str, plain_password: str) -> User:
        user = self._db.query(User).filter(User.username == username).first()

        # Mensaje idéntico si el usuario no existe o si la contraseña es
        # incorrecta — no revelar cuál de las dos falló (evita enumeración
        # de usuarios válidos por fuerza bruta).
        generic_error = "Usuario o contraseña incorrectos."

        if user is None:
            self._audit.log("LOGIN_FAILED", f"User:unknown:{username}", success=False,
                             detail="Usuario no existe")
            raise AuthenticationError(generic_error)

        if not user.is_active:
            self._audit.log("LOGIN_FAILED", f"User:{user.id}", success=False,
                             detail="Usuario inactivo", user_id=user.id)
            raise AuthenticationError(generic_error)

        if not verify_password(plain_password, user.password_hash):
            self._audit.log("LOGIN_FAILED", f"User:{user.id}", success=False,
                             detail="Password incorrecto", user_id=user.id)
            raise AuthenticationError(generic_error)

        self._audit.log("LOGIN_SUCCESS", f"User:{user.id}", user_id=user.id)
        return user

    def list_users(self) -> list[User]:
        return self._db.query(User).order_by(User.username).all()

    def set_active(self, target_user_id: int, is_active: bool, acting_admin_id: int) -> User:
        if target_user_id == acting_admin_id and not is_active:
            raise SelfLockoutError("No puedes desactivar tu propia cuenta.")

        user = self._db.get(User, target_user_id)
        if user is None:
            raise ValueError(f"Usuario {target_user_id} no existe.")

        user.is_active = is_active
        self._db.flush()
        self._audit.log(
            "USER_ACTIVE_TOGGLED", f"User:{user.id}",
            detail=f"is_active={is_active}", user_id=acting_admin_id,
        )
        return user

    def change_role(self, target_user_id: int, new_role: UserRole, acting_admin_id: int) -> User:
        if target_user_id == acting_admin_id and new_role != UserRole.ADMIN:
            raise SelfLockoutError("No puedes quitarte a ti mismo el rol ADMIN.")

        user = self._db.get(User, target_user_id)
        if user is None:
            raise ValueError(f"Usuario {target_user_id} no existe.")

        old_role = user.role.value
        user.role = new_role
        self._db.flush()
        self._audit.log(
            "USER_ROLE_CHANGED", f"User:{user.id}",
            detail=f"{old_role} -> {new_role.value}", user_id=acting_admin_id,
        )
        return user
