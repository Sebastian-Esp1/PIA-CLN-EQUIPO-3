"""Aggregates Ingrediente, Producto, Promoción y Domain Services."""

from datetime import datetime, time
from decimal import Decimal

import pytest

from src.domain.entities import Cliente, Ingrediente, Pedido, Producto, Promocion
from src.domain.errors import DatoInvalido, ExistenciaInsuficiente
from src.domain.services import ConsumoDeIngredientes, DisponibilidadProductos, EvaluadorPromociones
from src.domain.specifications import CanalEn, EvaluacionPedido, TotalMinimo
from src.domain.value_objects import (
    Disponibilidad,
    EstacionCocina,
    RequerimientoIngrediente,
    TipoMovimiento,
    UmbralCritico,
    VentanaHoraria,
)

pytestmark = pytest.mark.unit
T0 = datetime(2026, 11, 5, 17, 0)


def ingrediente(existencia=10, umbral=3, iid="I1"):
    return Ingrediente(iid, f"Insumo {iid}", Decimal(existencia), UmbralCritico(Decimal(umbral)))


def producto(receta=None, agotado=False):
    receta = receta or [RequerimientoIngrediente("I1", Decimal(2))]
    return Producto("P1", "Hamburguesa", Decimal("100"), EstacionCocina.PARRILLA, receta, agotado)


# --- Ingrediente ----------------------------------------------------------------------------
def test_entrada_y_salida_actualizan_existencia_y_registran_movimiento():  # RN-10
    i = ingrediente()
    i.registrar_entrada(5, "enc", T0, "compra")
    i.registrar_salida(3, "enc", T0)
    assert i.existencia == Decimal(12)
    assert [m.tipo for m in i.movimientos_nuevos] == [TipoMovimiento.ENTRADA, TipoMovimiento.SALIDA]
    assert [m.delta for m in i.movimientos_nuevos] == [Decimal(5), Decimal(-3)]
    assert i.movimientos_nuevos[-1].existencia_resultante == Decimal(12)


def test_salida_mayor_a_la_existencia_se_rechaza():  # INV-I1
    i = ingrediente(existencia=2)
    with pytest.raises(ExistenciaInsuficiente):
        i.registrar_salida(3, "enc", T0)
    assert i.existencia == Decimal(2) and not i.movimientos_nuevos


@pytest.mark.parametrize("cantidad", [0, -5, True, "x"])
def test_cantidades_invalidas(cantidad):
    with pytest.raises(DatoInvalido):
        ingrediente().registrar_entrada(cantidad, "enc", T0)
    with pytest.raises(DatoInvalido):
        ingrediente().registrar_salida(cantidad, "enc", T0)


def test_existencia_inicial_no_puede_ser_negativa():
    with pytest.raises(DatoInvalido):
        ingrediente(existencia=-1)


def test_conteo_ajusta_la_existencia_con_la_diferencia():
    i = ingrediente(existencia=10)
    i.registrar_conteo(7, "enc", T0)
    assert i.existencia == Decimal(7) and i.movimientos_nuevos[0].delta == Decimal(-3)
    with pytest.raises(DatoInvalido):
        i.registrar_conteo(-1, "enc", T0)


def test_es_critico_es_derivado_y_el_evento_se_emite_solo_al_cruzar():  # INV-I3, RN-11
    i = ingrediente(existencia=5, umbral=3)
    assert not i.es_critico
    i.registrar_salida(2, "enc", T0)  # 3 <= 3 -> cruza
    assert i.es_critico
    nombres = [e.nombre for e in i.extraer_eventos()]
    assert nombres == ["ExistenciaActualizada", "IngredienteMarcadoCritico"]
    i.registrar_salida(1, "enc", T0)  # ya era crítico: no repite el evento
    assert [e.nombre for e in i.extraer_eventos()] == ["ExistenciaActualizada"]
    i.definir_umbral(UmbralCritico(0))
    assert not i.es_critico


# --- Producto -------------------------------------------------------------------------------
def test_producto_exige_receta_y_cambia_de_estado():  # INV-R1, US-05
    with pytest.raises(DatoInvalido):
        Producto("P", "x", Decimal(1), EstacionCocina.BEBIDAS, [])
    p = producto()
    p.marcar_agotado("enc", T0)
    assert p.agotado
    p.reactivar("enc", T0)
    assert not p.agotado
    assert [e.nombre for e in p.extraer_eventos()] == ["ProductoMarcadoAgotado", "ProductoReactivado"]
    p.cambiar_receta([RequerimientoIngrediente("I9", Decimal(1))])
    assert p.receta[0].ingrediente_id == "I9"
    with pytest.raises(DatoInvalido):
        p.cambiar_receta([])


# --- Domain Services ------------------------------------------------------------------------
def test_disponibilidad_considera_agotado_receta_e_ingredientes():  # RN-02, RN-12
    servicio = DisponibilidadProductos()
    ingredientes = {"I1": ingrediente(existencia=5)}
    assert servicio.evaluar(producto(), 2, ingredientes).disponible  # necesita 4
    assert not servicio.evaluar(producto(), 3, ingredientes).disponible  # necesita 6
    assert "agotado" in servicio.evaluar(producto(agotado=True), 1, ingredientes).motivo
    assert "falta el ingrediente" in servicio.evaluar(producto(), 1, {}).motivo
    assert isinstance(servicio.evaluar(producto(), 1, ingredientes), Disponibilidad)


def test_consumo_descuenta_y_reintegra_segun_receta():  # SP-04, SP-08
    pedido = Pedido.iniciar("PED-1", "MESA", "C1", "ana", T0)
    prod = producto()
    pedido.agregar_linea(prod, 2, Disponibilidad.si(), "ana", T0)
    pedido.agregar_linea(prod, 1, Disponibilidad.si(), "ana", T0)
    ingredientes = {"I1": ingrediente(existencia=10)}
    consumo = ConsumoDeIngredientes()
    assert consumo.necesidades(pedido, {"P1": prod}) == {"I1": Decimal(6)}
    consumo.descontar(pedido, {"P1": prod}, ingredientes, "ana", T0)
    assert ingredientes["I1"].existencia == Decimal(4)
    consumo.reintegrar(pedido, {"P1": prod}, ingredientes, "ana", T0)
    assert ingredientes["I1"].existencia == Decimal(10)
    assert ingredientes["I1"].movimientos_nuevos[-1].referencia == "cancelación PED-1"


def test_consumo_sin_existencia_lanza_error_de_negocio():
    pedido = Pedido.iniciar("PED-1", "MESA", "C1", "ana", T0)
    prod = producto()
    pedido.agregar_linea(prod, 5, Disponibilidad.si(), "ana", T0)
    with pytest.raises(ExistenciaInsuficiente):
        ConsumoDeIngredientes().descontar(pedido, {"P1": prod}, {"I1": ingrediente(existencia=3)}, "a", T0)


# --- Promoción ------------------------------------------------------------------------------
def promo(pid="PR", inicio=time(16, 0), fin=time(19, 0), condiciones=None, pct=10, vigente=True):
    return Promocion(
        pid, "Happy", VentanaHoraria(inicio, fin), condiciones or [TotalMinimo(100)], Decimal(pct), vigente
    )


def evaluacion(total=200, canal="MESA", momento=T0):
    pedido = Pedido.iniciar("PED-1", canal, "C1", "ana", momento)
    prod = Producto("P1", "x", Decimal(total), EstacionCocina.PARRILLA, [RequerimientoIngrediente("I1", 1)])
    pedido.agregar_linea(prod, 1, Disponibilidad.si(), "ana", momento)
    return EvaluacionPedido(pedido, Cliente("C1", "Ana"), momento)


def test_promocion_exige_condicion_y_descuento_valido():  # INV-M2
    with pytest.raises(DatoInvalido):
        Promocion("PR", "x", VentanaHoraria(time(1), time(2)), [], 5)
    with pytest.raises(DatoInvalido):
        promo(pct=101)


def test_promocion_aplica_solo_vigente_en_horario_y_con_todas_las_condiciones():  # INV-M3, RN-13
    condiciones = [TotalMinimo(100), CanalEn("MESA")]
    assert promo(condiciones=condiciones).evaluar(evaluacion())
    assert not promo(condiciones=condiciones).evaluar(evaluacion(total=50))  # no cumple total
    assert not promo(condiciones=condiciones).evaluar(evaluacion(canal="DOMICILIO"))
    assert not promo(condiciones=condiciones).evaluar(evaluacion(momento=datetime(2026, 11, 5, 22, 0)))
    desactivada = promo()
    desactivada.desactivar()
    assert not desactivada.evaluar(evaluacion())
    desactivada.activar()
    assert desactivada.evaluar(evaluacion())


def test_descuento_se_redondea_a_centavos():
    assert promo(pct=Decimal("12.5")).calcular_descuento(Decimal("99.99")) == Decimal("12.50")


def test_evaluador_elige_la_promocion_con_mayor_descuento():
    ev = evaluacion()
    elegida = EvaluadorPromociones().aplicable(ev, [promo("A", pct=5), promo("B", pct=20), promo("C", pct=10)])
    assert elegida.promocion_id == "B"
    assert EvaluadorPromociones().aplicable(ev, []) is None
    assert EvaluadorPromociones().aplicable(ev, [promo(vigente=False)]) is None
