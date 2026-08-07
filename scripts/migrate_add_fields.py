"""
Migración: Agrega campos de captura logística y embarque a sales_orders.
Ejecutar: python -m scripts.migrate_add_fields
"""
from infrastructure.db.session import get_session, engine as db_engine  # <-- Importar engine como db_engine
from sqlalchemy import text, inspect

def migrate():
    # Usar db_engine en lugar de engine
    inspector = inspect(db_engine)
    columns = [col['name'] for col in inspector.get_columns('sales_orders')]
    
    new_cols = [
        'cajas', 'bolsas', 'fecha_envio', 'fecha_entrega', 'ubicacion',
        'paqueteria', 'valor_mxn', 'numero_guia', 'archivo_guia',
        'horario_entrega', 'quien_entrega', 'chofer_recibe',
        'fecha_salida', 'hora_salida', 'dias_estancia'
    ]
    
    with get_session() as db:
        for col in new_cols:
            if col not in columns:
                print(f"Agregando columna: {col}")
                db.execute(text(f"ALTER TABLE sales_orders ADD COLUMN {col} TEXT"))
        db.commit()
        print("✅ Migración completada.")

if __name__ == "__main__":
    migrate()