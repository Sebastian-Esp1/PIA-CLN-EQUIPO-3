"""Paquete del docente: 120 casos de prueba y 20 transiciones, con oráculo independiente del código.

El oráculo se calcula SOLO con los CSV (sin usar el dominio), de modo que no valida el código con él mismo.
"""

import csv
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

import pytest

from src.domain.specifications import EvaluacionPedido, califica_beneficio, puede_procesarse

pytestmark = pytest.mark.integration
DATA = Path(__file__).resolve().parents[2] / "data"


def leer(nombre):
    with open(DATA / nombre, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


ACTORES = {r["actor_id"]: r for r in leer("actores.csv")}
CATALOGO = {r["recurso_id"]: r for r in leer("catalogo.csv")}
OPERACIONES = {r["operacion_id"]: r for r in leer("operaciones.csv")}
DETALLE = defaultdict(list)
for fila in leer("detalle_operaciones.csv"):
    DETALLE[fila["operacion_id"]].append(fila)
CASOS = leer("casos_prueba.csv")
TRANSICIONES = leer("transiciones_prueba.csv")


def total_csv(operacion_id):
    return sum(
        (Decimal(CATALOGO[d["recurso_id"]]["precio_mxn"]) * int(d["cantidad"]) for d in DETALLE[operacion_id]),
        Decimal(0),
    )


def esperado_validar(operacion_id):  # R1
    op = OPERACIONES[operacion_id]
    return ACTORES[op["actor_id"]]["activo"] == "1" and bool(DETALLE[operacion_id]) and op["autorizado"] == "1"


def esperado_beneficio(operacion_id):  # R2
    op = OPERACIONES[operacion_id]
    return (
        ACTORES[op["actor_id"]]["es_preferente"] == "1"
        and total_csv(operacion_id) >= 1500
        and op["promocion_activa"] != "1"
    )


def test_el_paquete_tiene_el_tamano_esperado(datos):
    assert (len(ACTORES), len(CATALOGO), len(OPERACIONES), len(CASOS), len(TRANSICIONES)) == (40, 20, 60, 120, 20)
    assert sum(len(v) for v in DETALLE.values()) == 117


@pytest.mark.parametrize("caso", CASOS, ids=[c["caso_id"] for c in CASOS])
def test_casos_de_prueba_del_docente(datos, caso):
    with datos.uow_factory() as uow:
        pedido = uow.pedidos.obtener_por_id(caso["operacion_id"])
        cliente = uow.clientes.obtener_por_id(pedido.cliente_id)
        evaluacion = EvaluacionPedido(pedido, cliente, pedido.creado_en)
        assert pedido.total == total_csv(caso["operacion_id"])
        if caso["tipo_prueba"] == "validar_operacion":
            assert puede_procesarse().es_satisfecha_por(evaluacion) is esperado_validar(caso["operacion_id"])
        else:
            assert califica_beneficio().es_satisfecha_por(evaluacion) is esperado_beneficio(caso["operacion_id"])


def test_el_conjunto_cubre_casos_positivos_y_negativos(datos):
    validar = {esperado_validar(c["operacion_id"]) for c in CASOS if c["tipo_prueba"] == "validar_operacion"}
    beneficio = {esperado_beneficio(c["operacion_id"]) for c in CASOS if c["tipo_prueba"] == "evaluar_beneficio"}
    assert validar == {True, False} and beneficio == {True, False}


# --- 20 transiciones ----------------------------------------------------------------------------
ENCARGADO = {"X-Usuario": "encargado1", "X-Rol": "ENCARGADO"}


def productos_disponibles(operacion_id):
    """Oráculo de disponibilidad: habilitado y existencia suficiente (cada unidad usa 1 de existencia)."""
    return all(
        CATALOGO[d["recurso_id"]]["habilitado"] == "1"
        and Decimal(CATALOGO[d["recurso_id"]]["capacidad_o_stock"]) >= int(d["cantidad"])
        for d in DETALLE[operacion_id]
    )


def confirmar(api, op):
    return api.post(f"/pedidos/{op}/confirmar", headers=ENCARGADO)


def avanzar_hasta_listo(api, op):
    pedido = api.get(f"/pedidos/{op}").json()
    for linea in pedido["lineas"]:
        base = f"/cocina/pedidos/{op}/lineas/{linea['linea_id']}"
        assert api.post(f"{base}/iniciar", headers=ENCARGADO).status_code == 200
        assert api.post(f"{base}/listo", headers=ENCARGADO).status_code == 200


@pytest.mark.parametrize("caso", TRANSICIONES, ids=[t["caso_id"] for t in TRANSICIONES])
def test_transiciones_del_docente(api, caso):
    op, accion = caso["operacion_id"], caso["accion_sugerida"]
    procesable = esperado_validar(op) and productos_disponibles(op)
    assert api.get(f"/pedidos/{op}").json()["estado"] == "EN_REGISTRO"  # parten del estado inicial

    if accion == "aprobar":
        r = confirmar(api, op)
        if procesable:
            assert r.status_code == 200 and r.json()["estado"] == "CONFIRMADO"
        else:
            assert r.status_code == 409 and r.json()["codigo"] in {"PEDIDO_NO_PROCESABLE", "PRODUCTO_NO_DISPONIBLE"}
            assert api.get(f"/pedidos/{op}").json()["estado"] == "EN_REGISTRO"
    elif accion == "completar":
        r = confirmar(api, op)
        if not procesable:
            assert r.status_code == 409
            return
        avanzar_hasta_listo(api, op)
        r = api.post(f"/pedidos/{op}/cerrar", headers=ENCARGADO)
        assert r.status_code == 200 and r.json()["estado"] == "CERRADO"
    elif accion == "cancelar":
        r = api.post(f"/pedidos/{op}/cancelar", json={"motivo": "prueba del docente"}, headers=ENCARGADO)
        assert r.status_code == 200 and r.json()["estado"] == "CANCELADO"
        assert r.json()["cancelacion"]["motivo"] == "prueba del docente"
    elif accion == "repetir_aprobacion":
        primera = confirmar(api, op)
        segunda = confirmar(api, op)
        assert segunda.status_code == 409  # nunca se aprueba dos veces
        if procesable:
            assert primera.status_code == 200 and segunda.json()["codigo"] == "TRANSICION_INVALIDA"
    elif accion == "saltar_estado":
        r = api.post(f"/pedidos/{op}/cerrar", headers=ENCARGADO)
        assert r.status_code == 409 and r.json()["codigo"] == "TRANSICION_INVALIDA"
        assert api.get(f"/pedidos/{op}").json()["estado"] == "EN_REGISTRO"
    else:  # pragma: no cover - protege contra acciones nuevas en el CSV
        pytest.fail(f"acción no cubierta: {accion}")
