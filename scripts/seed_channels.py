"""
Seed de canales logísticos. settings.CHANNELS queda solo como la lista
inicial de referencia -- la fuente de verdad real pasa a ser la tabla
`channels`. Correr una sola vez (es idempotente: si el canal ya existe,
lo salta).

Uso:
    python -m scripts.seed_channels
"""
from __future__ import annotations
import sys

sys.path.insert(0, ".")

from infrastructure.db.session import init_db, get_session
from core.models.entities import Channel
from config.settings import settings

_DEFAULT_NAMES = {
    "VL": "Venta Local",
    "PEGE": "PEGE",
    "TIAU": "Tienda Autoservicio",
    "MUESTRAS": "Muestras",
    "AMAZON": "Amazon",
    "MH": "Mayoreo/Handling",  # ajustar al nombre real del negocio si difiere
}


def main() -> None:
    init_db()
    with get_session() as db:
        existing_codes = {c.code for c in db.query(Channel).all()}
        created = 0
        for code in settings.CHANNELS:
            if code in existing_codes:
                continue
            db.add(Channel(code=code, name=_DEFAULT_NAMES.get(code, code), is_active=True))
            created += 1
        print(f"Canales creados: {created}. Ya existían: {len(existing_codes)}.")


if __name__ == "__main__":
    main()
