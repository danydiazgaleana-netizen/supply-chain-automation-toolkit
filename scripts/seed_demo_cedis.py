"""
Datos de demostración para la reunión con el CEDIS -- todos los nombres y
números son FICTICIOS. IDEMPOTENTE: si ya existen las OVs de demo (de una
corrida anterior), las borra primero y las recrea limpias, para que se
pueda correr este script las veces que haga falta sin tronar.

  1. OV 1036 (Raúl): discrepancia de CAJAS Y número de pedido. Despacho bloqueado.
  2. OV 2050 (María): discrepancia SOLO de cajas. Despacho bloqueado.
  3. OV 3071 (Carlos): TODO coincide. Sin bloqueo -- demuestra que no hay falsos positivos.

Uso:
    python -m scripts.seed_demo_cedis
"""
from __future__ import annotations
import sys
sys.path.insert(0, ".")

from infrastructure.db.session import init_db, get_session
from core.models.entities import Channel, UserRole, SalesOrder, Discrepancia
from gui.controllers.sales_order_controller import SalesOrderController
from core.services.shipment_service import ShipmentService
from core.schemas.validators import ShipmentUpdateSchema

_DEMO_ORDER_NUMBERS = ("1036", "2050", "3071")


def _reset_demo_data(db) -> None:
    """Borra corridas anteriores del demo para que el script sea repetible."""
    orders = db.query(SalesOrder).filter(SalesOrder.order_number.in_(_DEMO_ORDER_NUMBERS)).all()
    for order in orders:
        db.query(Discrepancia).filter(Discrepancia.sales_order_id == order.id).delete()
        db.delete(order)  # cascade="all, delete-orphan" se lleva los shipments
    if orders:
        db.flush()
        print(f"(Se limpiaron {len(orders)} OV(s) de una corrida anterior del demo)")


def _ensure_channel(db, code, name) -> None:
    if not db.query(Channel).filter(Channel.code == code).first():
        db.add(Channel(code=code, name=name, is_active=True))


def main() -> None:
    init_db()
    with get_session() as db:
        _reset_demo_data(db)
        _ensure_channel(db, "VL", "Venta Local")
        _ensure_channel(db, "PEGE", "PEGE")

    ctrl = SalesOrderController(current_user_role=UserRole.ADMIN, current_user_id=None)

    print("=== Escenario 1: OV 1036 (Raúl) -- discrepancia de cajas Y pedido ===")
    r1 = ctrl.create_order(order_number="1036", customer_name="Raúl", channel="VL",
                            cajas="10", numero_pedido_logistica="GLS2026-133-1036")
    print(" Logística captura:", r1.message)
    with get_session() as db:
        order = db.query(SalesOrder).filter(SalesOrder.order_number == "1036").first()
        sid = order.shipments[0].id
    with get_session() as db:
        ShipmentService(db).update_shipment_detalles(
            sid, ShipmentUpdateSchema(numero_pedido="GLS2026-134-1036", cajas=12,
                                       chofer="Juan Pérez", fecha_entrega="2026-08-27", version=1),
            UserRole.ADMIN, None,
        )
    print(" Embarques captura: 12 cajas, pedido GLS2026-134-1036 (distinto)")

    print("\n=== Escenario 2: OV 2050 (María) -- solo discrepancia de cajas ===")
    r2 = ctrl.create_order(order_number="2050", customer_name="María", channel="PEGE",
                            cajas="20", numero_pedido_logistica="PEGE2026-200-2050")
    print(" Logística captura:", r2.message)
    with get_session() as db:
        order2 = db.query(SalesOrder).filter(SalesOrder.order_number == "2050").first()
        sid2 = order2.shipments[0].id
    with get_session() as db:
        ShipmentService(db).update_shipment_detalles(
            sid2, ShipmentUpdateSchema(numero_pedido="PEGE2026-200-2050", cajas=18,
                                        chofer="Ana López", fecha_entrega="2026-08-28", version=1),
            UserRole.ADMIN, None,
        )
    print(" Embarques captura: 18 cajas (declaradas 20), mismo número de pedido")

    print("\n=== Escenario 3: OV 3071 (Carlos) -- todo coincide, sin bloqueo ===")
    r3 = ctrl.create_order(order_number="3071", customer_name="Carlos", channel="VL",
                            cajas="8", numero_pedido_logistica="VL2026-071-3071")
    print(" Logística captura:", r3.message)
    with get_session() as db:
        order3 = db.query(SalesOrder).filter(SalesOrder.order_number == "3071").first()
        sid3 = order3.shipments[0].id
    with get_session() as db:
        ShipmentService(db).update_shipment_detalles(
            sid3, ShipmentUpdateSchema(numero_pedido="VL2026-071-3071", cajas=8,
                                        chofer="Pedro Ruiz", fecha_entrega="2026-08-28", version=1),
            UserRole.ADMIN, None,
        )
    print(" Embarques captura: 8 cajas, mismo número de pedido -- CONCILIADO")

    print("\n=== Datos de demo listos. Abre 'Embarques' o 'Discrepancias' en la app. ===")


if __name__ == "__main__":
    main()
