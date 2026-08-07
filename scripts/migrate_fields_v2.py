"""
Migración de campos adicionales para SalesOrder.
Ejecutar: python -m scripts.migrate_fields_v2
"""
from infrastructure.db.session import get_session
from sqlalchemy import inspect, text

def migrate():
    with get_session() as db:
        inspector = inspect(db.get_bind())
        columns = [col['name'] for col in inspector.get_columns('sales_orders')]
        
        new_cols = [
            'cajas', 'bolsas', 'fecha_envio', 'fecha_entrega', 'ubicacion',
            'paqueteria', 'valor_mxn', 'numero_guia', 'archivo_guia',
            'horario_entrega', 'quien_entrega', 'chofer_recibe',
            'fecha_salida', 'hora_salida', 'dias_estancia'
        ]
        
        for col in new_cols:
            if col not in columns:
                print(f"✅ Agregando columna: {col}")
                db.execute(text(f"ALTER TABLE sales_orders ADD COLUMN {col} TEXT"))
            else:
                print(f"⏩ Columna ya existe: {col}")
        
        db.commit()
        print("✅ Migración completada.")

if __name__ == "__main__":
    migrate()