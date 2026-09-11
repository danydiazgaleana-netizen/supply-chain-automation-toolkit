import pytest
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Reemplaza 'core.models.entities' con la ruta real de tu modulo de modelos
from core.models.entities import (
    Base,
    Channel,
    SalesOrder,
    Shipment,
    SalesOrderStatus,
    ShipmentStatus
)

# ----------------------------------------------------------------------
# Configuración del Engine de SQLite en memoria
# ----------------------------------------------------------------------
# Use StaticPool to ensure the same connection is reused across the test thread
# for in-memory SQLite, preventing the database from disappearing between operations.
SQLITE_IN_MEMORY_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def db_engine():
    """Crea un motor SQLite en memoria reutilizable durante la sesión de pruebas."""
    engine = create_engine(
        SQLITE_IN_MEMORY_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    yield engine
    engine.dispose()


@pytest.fixture(scope="function", autouse=True)
def db_session(db_engine) -> Generator[Session, None, None]:
    """
    Crea un esquema limpio antes de cada prueba y destruye las tablas al finalizar.
    Garantiza el aislamiento total entre tests y evita errores de duplicado.
    """
    Base.metadata.create_all(bind=db_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=db_engine)


# ----------------------------------------------------------------------
# Fixtures de Datos Maestros (Semillas para pruebas)
# ----------------------------------------------------------------------

@pytest.fixture
def sample_channel(db_session: Session) -> Channel:
    """Fixture que provee un canal activo por defecto."""
    channel = Channel(
        code="DIR-MX",
        name="Venta Directa México",
        is_active=True
    )
    db_session.add(channel)
    db_session.commit()
    db_session.refresh(channel)
    return channel


@pytest.fixture
def inactive_channel(db_session: Session) -> Channel:
    """Fixture que provee un canal inactivo para probar validaciones de inactividad."""
    channel = Channel(
        code="INACT-01",
        name="Canal Descontinuado",
        is_active=False
    )
    db_session.add(channel)
    db_session.commit()
    db_session.refresh(channel)
    return channel


@pytest.fixture
def sample_sales_order(db_session: Session, sample_channel: Channel) -> SalesOrder:
    """Fixture que crea una orden de venta ligada al canal activo mediante FK (channel_id)."""
    order = SalesOrder(
        order_number="OV-2026-0001",
        customer_name="Empresa Ejemplo S.A.",
        channel_id=sample_channel.id,
        created_by_id=101,
        status=SalesOrderStatus.ACTIVE,
        version=1
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    return order


@pytest.fixture
def sample_shipment(db_session: Session, sample_sales_order: SalesOrder) -> Shipment:
    """Fixture que crea un embarque pendiente asociado a la SalesOrder."""
    shipment = Shipment(
        sales_order_id=sample_sales_order.id,
        status=ShipmentStatus.PENDING,
        tracking_number="TRACK-998877",
        driver_name="Juan Pérez",
        version=1
    )
    db_session.add(shipment)
    db_session.commit()
    db_session.refresh(shipment)
    return shipment