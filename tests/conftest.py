from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.aplicacion import crear_app
from src.api.contenedor import construir_contenedor
from src.infrastructure.config import Configuracion
from src.infrastructure.importacion_csv import importar

DATA = Path(__file__).resolve().parent.parent / "data"


class RelojFijo:
    """Reloj controlable para pruebas deterministas."""

    def __init__(self, inicio=datetime(2026, 11, 5, 12, 0, 0)):
        self.actual = inicio

    def ahora(self):
        return self.actual

    def avanzar(self, **kwargs):
        self.actual += timedelta(**kwargs)


@pytest.fixture
def reloj():
    return RelojFijo()


@pytest.fixture
def contenedor(reloj):
    cfg = Configuracion(database_url="sqlite://", data_dir=str(DATA))
    c = construir_contenedor(cfg, reloj)
    yield c
    c.motor.dispose()


@pytest.fixture
def datos(contenedor):
    """Contenedor con el paquete de datos del docente ya cargado."""
    importar(contenedor.uow_factory, DATA)
    return contenedor


@pytest.fixture
def api(datos):
    with TestClient(crear_app(datos)) as cliente:
        yield cliente
