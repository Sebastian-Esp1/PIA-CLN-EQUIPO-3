"""Specification con composición AND/OR/NOT y las reglas R1/R2 del paquete del docente."""

from datetime import datetime, time
from decimal import Decimal

import pytest

from src.domain.entities import Cliente, Pedido
from src.domain.specifications import (
    CanalEn,
    ClienteActivo,
    ClientePreferente,
    DentroDeVentana,
    EvaluacionPedido,
    PedidoAutorizado,
    PedidoConLineas,
    TienePromocionActiva,
    TotalMinimo,
    califica_beneficio,
    puede_procesarse,
)
from src.domain.value_objects import CanalVenta, EstacionCocina, VentanaHoraria

pytestmark = pytest.mark.unit
AHORA = datetime(2026, 11, 5, 17, 0)


class ProductoFalso:
    def __init__(self, precio):
        self.producto_id, self.precio, self.estacion = "P1", Decimal(precio), EstacionCocina.PARRILLA


def evaluacion(total="0", activo=True, preferente=False, autorizado=True, promo=None, canal="MESA"):
    pedido = Pedido("PED-1", CanalVenta(canal), "C1", AHORA, autorizado=autorizado, promocion_id=promo)
    if Decimal(total) > 0:
        from src.domain.entities import LineaPedido

        pedido.lineas.append(LineaPedido(1, "P1", 1, Decimal(total), EstacionCocina.PARRILLA))
    return EvaluacionPedido(pedido, Cliente("C1", "Ana", activo, preferente), AHORA)


def test_especificaciones_simples():
    ev = evaluacion("100", activo=False, preferente=True, autorizado=False, promo="X")
    assert not ClienteActivo().es_satisfecha_por(ev)
    assert ClientePreferente().es_satisfecha_por(ev)
    assert PedidoConLineas().es_satisfecha_por(ev)
    assert not PedidoAutorizado().es_satisfecha_por(ev)
    assert TienePromocionActiva().es_satisfecha_por(ev)
    assert TotalMinimo(100).es_satisfecha_por(ev) and not TotalMinimo("100.01").es_satisfecha_por(ev)
    assert CanalEn("MESA", "TELEFONO").es_satisfecha_por(ev)
    assert not CanalEn("DOMICILIO").es_satisfecha_por(ev)


def test_ventana_como_especificacion():
    ev = evaluacion("100")
    assert DentroDeVentana(VentanaHoraria(time(16, 0), time(18, 0))).es_satisfecha_por(ev)
    assert not DentroDeVentana(VentanaHoraria(time(8, 0), time(10, 0))).es_satisfecha_por(ev)


def test_composicion_and_or_not():
    ev = evaluacion("100", preferente=True)
    verdadera, falsa = ClientePreferente(), TotalMinimo(500)
    assert (verdadera & verdadera).es_satisfecha_por(ev)
    assert not (verdadera & falsa).es_satisfecha_por(ev)
    assert (verdadera | falsa).es_satisfecha_por(ev)
    assert not (falsa | falsa).es_satisfecha_por(ev)
    assert (~falsa).es_satisfecha_por(ev)
    assert not (~verdadera).es_satisfecha_por(ev)
    assert "Y" in (verdadera & falsa).descripcion and "O" in (verdadera | falsa).descripcion


def test_motivos_de_fallo_explican_que_hoja_fallo():
    ev = evaluacion("0", activo=False, autorizado=False)
    motivos = puede_procesarse().motivos_de_fallo(ev)
    assert len(motivos) == 3
    assert any("activo" in m for m in motivos) and any("autorizado" in m for m in motivos)
    assert puede_procesarse().motivos_de_fallo(evaluacion("10")) == []
    assert (ClientePreferente() | TotalMinimo(5)).motivos_de_fallo(evaluacion("1")) != []
    assert "NO" in (~ClienteActivo()).motivos_de_fallo(evaluacion("1"))[0]


@pytest.mark.parametrize(
    ("activo", "lineas", "autorizado", "esperado"),
    [
        (True, "10", True, True),
        (False, "10", True, False),
        (True, "0", True, False),
        (True, "10", False, False),
        (False, "0", False, False),
    ],
)
def test_r1_puede_procesarse(activo, lineas, autorizado, esperado):
    ev = evaluacion(lineas, activo=activo, autorizado=autorizado)
    assert puede_procesarse().es_satisfecha_por(ev) is esperado


@pytest.mark.parametrize(
    ("preferente", "total", "promo", "esperado"),
    [
        (True, "1500", None, True),  # límite exacto
        (True, "1499.99", None, False),
        (False, "9000", None, False),
        (True, "9000", "PROMO", False),
        (True, "1500.01", None, True),
    ],
)
def test_r2_califica_beneficio(preferente, total, promo, esperado):
    ev = evaluacion(total, preferente=preferente, promo=promo)
    assert califica_beneficio().es_satisfecha_por(ev) is esperado
