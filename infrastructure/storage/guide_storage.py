"""
Almacenamiento de archivos de guía (PDF).

ADR: el binario NUNCA se guarda en la base de datos (ni como BLOB). Se copia
a infrastructure/storage/guias/ con un nombre único, y solo la ruta relativa
se persiste en Shipment.archivo_guia_path. Guardar binarios en la BD infla
backups, ralentiza queries que no los necesitan, y en Postgres específicamente
degrada el rendimiento de índices en la misma tabla.
"""
from __future__ import annotations
import shutil
import uuid
from pathlib import Path

from config.settings import BASE_DIR

GUIAS_DIR = BASE_DIR / "infrastructure" / "storage" / "guias"


class InvalidFileTypeError(Exception):
    pass


def save_guide_file(source_path: str, shipment_reference: str) -> str:
    """
    Copia el PDF seleccionado al storage del proyecto con un nombre único
    (evita colisiones si dos embarques usan un archivo llamado igual, ej.
    'guia.pdf' subido por distintos operadores el mismo día).
    Regresa la ruta RELATIVA a guardar en Shipment.archivo_guia_path.
    """
    src = Path(source_path)
    if src.suffix.lower() != ".pdf":
        raise InvalidFileTypeError(f"Solo se aceptan archivos PDF, se recibió: {src.suffix}")
    if not src.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {source_path}")

    GUIAS_DIR.mkdir(parents=True, exist_ok=True)
    unique_name = f"{shipment_reference}_{uuid.uuid4().hex[:8]}.pdf"
    dest = GUIAS_DIR / unique_name
    shutil.copy(src, dest)
    return f"guias/{unique_name}"


def resolve_guide_path(relative_path: str) -> Path:
    return BASE_DIR / "infrastructure" / "storage" / relative_path
