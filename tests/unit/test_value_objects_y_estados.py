"""Value Objects y máquina de estados (RN-01, RN-08, SP-01, SP-02, INV-M1)."""

from datetime import datetime, time
from decimal import Decimal

import pytest

from src.domain.errors import DatoInvalido, TransicionDeEstadoInvalida
from src.domain.state_machine import MAQUINA_PEDIDO, EstadoPedido
from src.domain.value_objects import (
    Disponibilidad,
    Modificacion,
    RequerimientoIngrediente,
    TipoModificacion,
    UmbralCritico,
    VentanaHoraria,
    a_decimal,
)

pytestmark = pytest.mark.unit

E = EstadoPedido


@pytest.mark.parametrize(
    ("origen", "destino"),
    [
        (E.EN_REGISTRO, E.CONFIRMADO),
        (E.EN_REGISTRO, E.CANCELADO),
        (E.CONFIRMADO, E.EN_PREPARACION),
        (E.CONFIRMADO, E.CANCELADO),
        (E.EN_PREPARACION, E.LISTO),
        (E.EN_PREPARACION, E.CANCELADO),
        (E.LISTO, E.CERRADO),
    ],
)
def test_transiciones_permitidas(origen, destino):
    assert MAQUINA_PEDIDO.puede(origen, destino)
    MAQUINA_PEDIDO.validar(origen, destino)  # no lanza


@pytest.mark.parametrize(
    ("origen", "destino"),
    [
        (E.EN_REGISTRO, E.LISTO),
        (E.EN_REGISTRO, E.CERRADO),
        (E.CONFIRMADO, E.CONFIRMADO),
        (E.CONFIRMADO, E.CERRADO),
        (E.LISTO, E.CANCELADO),
        (E.CERRADO, E.CANCELADO),
        (E.CANCELADO, E.CONFIRMADO),
        (E.CERRADO, E.EN_REGISTRO),
    ],
)
def test_transiciones_invalidas(origen, destino):
    assert not MAQUINA_PEDIDO.puede(origen, destino)
    with pytest.raises(TransicionDeEstadoInvalida):
        MAQUINA_PEDIDO.validar(origen, destino)


def test_estados_finales_no_tienen_destinos():
    assert MAQUINA_PEDIDO.destinos(E.CERRADO) == frozenset()
    assert E.CERRADO.es_final and E.CANCELADO.es_final and not E.LISTO.es_final


@pytest.mark.parametrize(
    ("estado", "modifica", "cancela"),
    [
        (E.EN_REGISTRO, True, True),
        (E.CONFIRMADO, True, True),
        (E.EN_PREPARACION, False, True),
        (E.LISTO, False, False),
        (E.CERRADO, False, False),
        (E.CANCELADO, False, False),
    ],
)
def test_matriz_de_modificacion_y_cancelacion(estado, modifica, cancela):  # SP-02
    assert estado.permite_modificar is modifica
    assert estado.permite_cancelar is cancela


def test_modificacion_exige_descripcion():
    assert Modificacion(TipoModificacion.QUITAR, "sin cebolla").descripcion == "sin cebolla"
    with pytest.raises(DatoInvalido):
        Modificacion(TipoModificacion.AGREGAR, "   ")


def test_ventana_horaria_valida_y_contiene():
    ventana = VentanaHoraria(time(16, 0), time(19, 0))
    assert ventana.contiene(datetime(2026, 11, 5, 17, 30))
    assert not ventana.contiene(datetime(2026, 11, 5, 20, 0))
    with pytest.raises(DatoInvalido):
        VentanaHoraria(time(19, 0), time(16, 0))  # INV-M1


def test_umbral_y_receta_rechazan_valores_invalidos():
    with pytest.raises(DatoInvalido):
        UmbralCritico(Decimal("-1"))
    assert UmbralCritico(0).cantidad == 0
    with pytest.raises(DatoInvalido):
        RequerimientoIngrediente("ING-1", Decimal("0"))


@pytest.mark.parametrize("valor", [True, None, "abc"])
def test_a_decimal_rechaza_no_numericos(valor):
    with pytest.raises(DatoInvalido):
        a_decimal(valor)


def test_disponibilidad_si_y_no():
    assert Disponibilidad.si().disponible
    no = Disponibilidad.no("agotado")
    assert not no.disponible and no.motivo == "agotado"
