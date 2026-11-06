"""Motor y fábrica de sesiones."""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.infrastructure.modelos import Base


def crear_motor(url: str) -> Engine:
    if url.startswith("sqlite") and (":memory:" in url or url in ("sqlite://", "sqlite:///")):
        # Una sola conexión compartida para que la base en memoria sobreviva entre sesiones.
        return create_engine(
            url, connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True)


def crear_tablas(motor: Engine) -> None:
    Base.metadata.create_all(motor)


def crear_fabrica_de_sesiones(motor: Engine) -> sessionmaker:
    return sessionmaker(bind=motor, expire_on_commit=False)
