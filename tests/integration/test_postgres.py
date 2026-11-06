"""Mismas reglas sobre PostgreSQL real. Se omite si no hay TEST_DATABASE_URL (CI y Docker Compose la definen)."""

import os

import pytest
from fastapi.testclient import TestClient

from src.api.aplicacion import crear_app
from src.api.contenedor import construir_contenedor
from src.infrastructure.config import Configuracion
from tests.conftest import DATA

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL no definida"),
]


def test_flujo_completo_sobre_postgresql():  # pragma: no cover - solo corre con PostgreSQL
    from sqlalchemy import text

    cfg = Configuracion(database_url=os.environ["TEST_DATABASE_URL"], data_dir=str(DATA), seed_on_start=True)
    c = construir_contenedor(cfg)
    with c.motor.begin() as conexion:  # base limpia para que la prueba sea repetible
        conexion.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    c.motor.dispose()
    c = construir_contenedor(cfg)
    try:
        with TestClient(crear_app(c)) as api:
            h = {"X-Usuario": "ci", "X-Rol": "GERENTE"}
            pid = api.post("/pedidos", json={"canal": "MESA", "cliente_id": "PED-C001"}, headers=h).json()["pedido_id"]
            assert api.post(f"/pedidos/{pid}/lineas", json={"producto_id": "PED-P001", "cantidad": 2}, headers=h).status_code == 201
            api.post(f"/pedidos/{pid}/autorizar", headers=h)
            r = api.post(f"/pedidos/{pid}/confirmar", headers=h)
            assert r.status_code == 200 and r.json()["estado"] == "CONFIRMADO"
            assert api.post(f"/pedidos/{pid}/confirmar", headers=h).status_code == 409
    finally:
        c.motor.dispose()
