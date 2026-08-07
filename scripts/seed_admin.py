"""
Seed del primer usuario ADMIN. Se ejecuta UNA vez, manualmente, desde
terminal — nunca desde la GUI, porque la GUI exige estar logueado como
ADMIN para crear usuarios, y el primer ADMIN todavía no existe.

Uso:
    python -m scripts.seed_admin
"""
from __future__ import annotations
import getpass
import sys

sys.path.insert(0, ".")

from infrastructure.db.session import init_db, get_session
from core.services.auth_service import AuthService, UserAlreadyExistsError
from core.models.entities import UserRole


def main() -> None:
    init_db()
    print("=== Creación del primer usuario ADMIN ===")
    username = input("Username: ").strip()
    full_name = input("Nombre completo: ").strip()
    password = getpass.getpass("Password (mín. 8 caracteres, no se muestra en pantalla): ")

    with get_session() as db:
        auth = AuthService(db)
        try:
            user = auth.create_user(
                username=username, plain_password=password,
                full_name=full_name, role=UserRole.ADMIN,
            )
            print(f"OK: ADMIN '{user.username}' creado (id={user.id}).")
        except UserAlreadyExistsError as exc:
            print(f"ERROR: {exc}")
        except ValueError as exc:
            print(f"ERROR: {exc}")


if __name__ == "__main__":
    main()
