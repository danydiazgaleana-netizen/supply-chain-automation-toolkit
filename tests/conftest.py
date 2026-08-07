"""
Fixtures compartidas. Regla central: CADA TEST corre contra una base de
datos SQLite temporal y nueva (tmp_path), nunca contra wms.db de desarrollo
ni contra Postgres real. Esto es lo que permite correr `pytest` sin efectos
secundarios sobre datos reales, y sin que un test deje basura para el
siguiente (aislamiento total).
"""
from __future__ import annotations
import os
import sys
import importlib
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture()
def db_url(tmp_path):
    """Ruta de DB única por test -- tmp_path la borra sola al terminar."""
    return f"sqlite:///{tmp_path / 'test_wms.db'}"


@pytest.fixture()
def db_session_factory(db_url, monkeypatch):
    """
    Reconstruye infrastructure.db.session con la URL temporal de este test.
    Necesario porque ese módulo crea el engine UNA vez al importarse -- si no
    lo recargamos, todos los tests compartirían el engine del primer test
    que corrió (justo el tipo de contaminación cruzada que un test suite
    debe evitar).
    """
    monkeypatch.setenv("WMS_DB_URL", db_url)

    import config.settings as settings_module
    importlib.reload(settings_module)

    import infrastructure.db.session as session_module
    importlib.reload(session_module)
    session_module.init_db()

    yield session_module.get_session


@pytest.fixture()
def seeded_channels(db_session_factory):
    """Canales base disponibles en cada test que los necesite."""
    from core.models.entities import Channel
    with db_session_factory() as db:
        for code, name in [
            ("VL", "Venta Local"), ("PEGE", "PEGE"), ("TIAU", "Tienda Autoservicio"),
            ("MUESTRAS", "Muestras"), ("AMAZON", "Amazon"), ("MH", "Mayoreo/Handling"),
        ]:
            db.add(Channel(code=code, name=name, is_active=True))
    return db_session_factory


@pytest.fixture()
def admin_and_operator(seeded_channels):
    """Dos usuarios base -- ADMIN y OPERADOR -- para pruebas de permisos."""
    from core.services.auth_service import AuthService
    from core.models.entities import UserRole

    with seeded_channels() as db:
        auth = AuthService(db)
        admin = auth.create_user("admin_test", "AdminPass123", "Admin Test", UserRole.ADMIN)
        operator = auth.create_user("op_test", "OperadorPass1", "Operador Test", UserRole.OPERADOR)
        return {"admin_id": admin.id, "operator_id": operator.id}
