"""
Estado de sesión en memoria. Deliberadamente simple (no es un JWT ni un token
persistente) porque esto es una app de escritorio de un solo proceso — pero
vive en un módulo propio para que el día que esto sea un backend FastAPI,
se reemplace por sesión de request/JWT sin tener que rastrear "current_user"
regado por 10 archivos de GUI.
"""
from __future__ import annotations
from dataclasses import dataclass

from core.models.entities import UserRole


@dataclass
class SessionState:
    user_id: int
    username: str
    full_name: str
    role: UserRole


class SessionManager:
    _current: SessionState | None = None

    @classmethod
    def login(cls, state: SessionState) -> None:
        cls._current = state

    @classmethod
    def logout(cls) -> None:
        cls._current = None

    @classmethod
    def current(cls) -> SessionState:
        if cls._current is None:
            raise RuntimeError("No hay sesión activa. Esto es un bug: la GUI no debería "
                                "llegar a este punto sin login previo.")
        return cls._current

    @classmethod
    def is_authenticated(cls) -> bool:
        return cls._current is not None
