"""Aggregate Pedido: invariantes INV-P1..P8, estados, eventos e historial (RN-01..RN-09, RN-13)."""

from datetime import datetime, time
from decimal import Decimal

import pytest

from src.domain import events as ev
from src.domain.entities import Cliente, Pedido, Producto, Promocion
from src.domain.errors import (
    CancelacionNoPermitida,
    DatoInvalido,
    MotivoDeCancelacionRequerido,
    PedidoNoModificable,
    PedidoNoProcesable,
    TransicionDeEstadoInvalida,
)
from src.domain.specifications import TotalMinimo
from src.domain.state_machine import EstadoPedido
from src.domain.value_objects import (
    Disponibilidad,
    EstacionCocina,
    EstadoPreparacion,
    RequerimientoIngrediente,
    VentanaHoraria,
)

pytestmark = pytest.mark.unit
T0 = datetime(2026, 11, 5, 12, 0)
SI = Disponibilidad.si()
CLIENTE = Cliente("C1", "Ana")


def producto(pid="P1", precio="100", estacion=EstacionCocina.PARRILLA):
    return Producto(pid, f"Plato {pid}", Decimal(precio), estacion, [RequerimientoIngrediente("I1", 1)])


def pedido_con_lineas(*cantidades, autorizado=True):
    p = Pedido.iniciar("PED-1", "MESA", "C1", "ana", T0)
    for i, cantidad in enumerate(cantidades, start=1):
        assert p.agregar_linea(producto(f"P{i}"), cantidad, SI, "ana", T0).agregada
    if autorizado:
        p.autorizar("ana", T0)
    return p


def nombres(pedido):
    return [e.nombre for e in pedido.extraer_eventos()]


def test_iniciar_pedido_registra_historial_y_evento():  # RN-01, RN-09
    p = Pedido.iniciar("PED-1", "whatsapp".upper(), "C1", "ana", T0)
    assert p.estado is EstadoPedido.EN_REGISTRO and p.canal.value == "WHATSAPP"
    assert p.historial[0].accion == "Pedido iniciado" and p.historial[0].usuario == "ana"
    assert nombres(p) == ["PedidoIniciado"]
    assert p.extraer_eventos() == []  # los eventos se entregan una sola vez


@pytest.mark.parametrize("canal", ["", "MOSTRADOR", None])
def test_canal_invalido_se_rechaza(canal):
    with pytest.raises(DatoInvalido):
        Pedido.iniciar("PED-1", canal, "C1", "ana", T0)


def test_pedido_necesita_cliente():
    with pytest.raises(DatoInvalido):
        Pedido.iniciar("PED-1", "MESA", "", "ana", T0)


def test_agregar_lineas_calcula_total_y_precio_vigente():
    p = pedido_con_lineas(2, 3)
    assert p.total == Decimal("500") and p.total_a_pagar == Decimal("500")
    assert [linea.linea_id for linea in p.lineas] == [1, 2]
    assert p.linea(2).estacion is EstacionCocina.PARRILLA
    with pytest.raises(DatoInvalido):
        p.linea(99)


@pytest.mark.parametrize("cantidad", [0, -1, True, 1.5, "2"])
def test_cantidad_debe_ser_entero_positivo(cantidad):  # INV-P1
    p = Pedido.iniciar("PED-1", "MESA", "C1", "ana", T0)
    with pytest.raises(DatoInvalido):
        p.agregar_linea(producto(), cantidad, SI, "ana", T0)


def test_producto_no_disponible_no_se_agrega_y_deja_incidencia():  # RN-02, INV-P2
    p = Pedido.iniciar("PED-1", "MESA", "C1", "ana", T0)
    p.extraer_eventos()
    resultado = p.agregar_linea(producto(), 1, Disponibilidad.no("agotado"), "ana", T0)
    assert not resultado.agregada and resultado.motivo == "agotado" and not p.lineas
    assert p.historial[-1].accion == "Producto rechazado por disponibilidad"
    assert nombres(p) == ["ProductoRechazadoPorDisponibilidad"]


def test_modificaciones_se_asocian_a_la_linea():  # RN-03
    p = pedido_con_lineas(1)
    p.agregar_modificacion(1, "QUITAR", "sin cebolla", "ana", T0)
    p.agregar_modificacion(1, "AGREGAR", "extra queso", "ana", T0)
    assert [m.descripcion for m in p.linea(1).modificaciones] == ["sin cebolla", "extra queso"]
    assert "ModificacionAgregada" in nombres(p)
    with pytest.raises(DatoInvalido):
        p.agregar_modificacion(1, "BORRAR", "x", "ana", T0)
    with pytest.raises(DatoInvalido):
        p.agregar_modificacion(7, "QUITAR", "x", "ana", T0)  # línea inexistente


def test_confirmar_exige_regla_r1_y_explica_el_motivo():  # RN-04
    p = pedido_con_lineas(1, autorizado=False)
    with pytest.raises(PedidoNoProcesable, match="autorizado"):
        p.confirmar("ana", CLIENTE, T0)
    assert p.estado is EstadoPedido.EN_REGISTRO
    vacio = Pedido.iniciar("PED-2", "MESA", "C1", "ana", T0)
    vacio.autorizar("ana", T0)
    with pytest.raises(PedidoNoProcesable, match="línea"):
        vacio.confirmar("ana", CLIENTE, T0)
    with pytest.raises(PedidoNoProcesable, match="activo"):
        pedido_con_lineas(1).confirmar("ana", Cliente("C1", "Ana", activo=False), T0)


def test_confirmar_cambia_estado_registra_y_emite():
    p = pedido_con_lineas(1)
    p.extraer_eventos()
    p.confirmar("ana", CLIENTE, T0)
    assert p.estado is EstadoPedido.CONFIRMADO
    assert p.historial[-1].accion == "Pedido confirmado"
    assert nombres(p) == ["PedidoConfirmado"]
    with pytest.raises(TransicionDeEstadoInvalida):  # no se confirma dos veces
        p.confirmar("ana", CLIENTE, T0)


def test_confirmar_aplica_beneficio_al_cliente_preferente():  # R2
    p = pedido_con_lineas(20)  # total 2000
    p.extraer_eventos()
    p.confirmar("ana", Cliente("C1", "Ana", es_preferente=True), T0)
    assert p.beneficio_aplicado
    assert "BeneficioPreferenteAplicado" in nombres(p)


def test_no_hay_beneficio_si_el_total_no_alcanza_o_hay_promocion():
    corto = pedido_con_lineas(5)
    corto.confirmar("ana", Cliente("C1", "Ana", es_preferente=True), T0)
    assert not corto.beneficio_aplicado
    con_promo = pedido_con_lineas(20)
    promo = Promocion("PR", "Happy", VentanaHoraria(time(0, 0), time(23, 59)), [TotalMinimo(1)], 10)
    con_promo.confirmar("ana", Cliente("C1", "Ana", es_preferente=True), T0, promo)
    assert not con_promo.beneficio_aplicado and con_promo.promocion_activa


def test_promocion_aplicada_calcula_descuento():  # RN-13
    p = pedido_con_lineas(10)  # 1000
    p.extraer_eventos()
    promo = Promocion("PR", "Diez", VentanaHoraria(time(0, 0), time(23, 59)), [TotalMinimo(1)], 10)
    p.confirmar("ana", CLIENTE, T0, promo)
    assert p.descuento == Decimal("100.00") and p.total_a_pagar == Decimal("900.00")
    assert "PromocionAplicada" in nombres(p)


def test_no_se_modifica_ni_se_agregan_lineas_fuera_de_estado():  # INV-P3, SP-02
    p = pedido_con_lineas(1)
    p.confirmar("ana", CLIENTE, T0)
    p.agregar_modificacion(1, "QUITAR", "sin sal", "ana", T0)  # CONFIRMADO sí admite cambios
    with pytest.raises(PedidoNoModificable):
        p.agregar_linea(producto("P9"), 1, SI, "ana", T0)  # pero no nuevas líneas
    p.iniciar_preparacion_de_linea(1, "chef", T0)
    with pytest.raises(PedidoNoModificable):
        p.agregar_modificacion(1, "QUITAR", "otra", "ana", T0)  # EN_PREPARACION ya no


def test_autorizar_solo_en_registro():
    p = pedido_con_lineas(1)
    p.confirmar("ana", CLIENTE, T0)
    with pytest.raises(PedidoNoModificable):
        p.autorizar("ana", T0)


def test_preparacion_por_linea_y_pedido_listo_al_terminar_todas():  # RN-05, RN-06, INV-P5
    p = pedido_con_lineas(1, 1)
    p.confirmar("ana", CLIENTE, T0)
    p.extraer_eventos()
    with pytest.raises(PedidoNoModificable):
        p.marcar_linea_lista(1, "chef", T0)  # aún no está en preparación
    p.iniciar_preparacion_de_linea(1, "chef", T0)
    assert p.estado is EstadoPedido.EN_PREPARACION
    with pytest.raises(DatoInvalido):
        p.iniciar_preparacion_de_linea(1, "chef", T0)  # ya iniciada
    assert p.marcar_linea_lista(1, "chef", T0) is False  # falta la línea 2
    assert p.estado is EstadoPedido.EN_PREPARACION
    p.iniciar_preparacion_de_linea(2, "chef", T0)
    assert p.marcar_linea_lista(2, "chef", T0) is True
    assert p.estado is EstadoPedido.LISTO
    assert nombres(p) == ["LineaPreparada", "LineaPreparada", "PedidoListo"]
    assert all(item.estado_preparacion is EstadoPreparacion.LISTA for item in p.lineas)


def test_linea_debe_estar_en_preparacion_para_marcarse_lista():
    p = pedido_con_lineas(1, 1)
    p.confirmar("ana", CLIENTE, T0)
    p.iniciar_preparacion_de_linea(1, "chef", T0)
    with pytest.raises(DatoInvalido):
        p.marcar_linea_lista(2, "chef", T0)  # la 2 sigue pendiente


def test_preparar_exige_pedido_confirmado():
    with pytest.raises(PedidoNoModificable):
        pedido_con_lineas(1).iniciar_preparacion_de_linea(1, "chef", T0)


def test_cerrar_solo_desde_listo_y_emite_evento_de_venta():  # RN-14
    p = pedido_con_lineas(2)
    with pytest.raises(TransicionDeEstadoInvalida):
        p.cerrar("ana", T0)  # saltar estado
    p.confirmar("ana", CLIENTE, T0)
    p.iniciar_preparacion_de_linea(1, "chef", T0)
    p.marcar_linea_lista(1, "chef", T0)
    p.extraer_eventos()
    p.cerrar("ana", T0)
    assert p.estado is EstadoPedido.CERRADO
    (evento,) = p.extraer_eventos()
    assert isinstance(evento, ev.PedidoCerrado)
    assert evento.detalle == {"total": "200", "unidades": 2, "canal": "MESA"}


def test_cancelar_exige_motivo_y_guarda_quien_cuando_y_por_que():  # RN-07, RN-09
    p = pedido_con_lineas(1)
    for motivo in ("", "   ", None):
        with pytest.raises(MotivoDeCancelacionRequerido):
            p.cancelar(motivo, "enc", T0)
    previo = p.cancelar("  cliente se fue ", "enc", T0)
    assert previo is EstadoPedido.EN_REGISTRO and p.estado is EstadoPedido.CANCELADO
    assert (p.cancelacion.motivo, p.cancelacion.usuario, p.cancelacion.fecha) == (
        "cliente se fue",
        "enc",
        T0,
    )
    assert p.historial[-1].detalle == "motivo: cliente se fue"
    assert "PedidoCancelado" in nombres(p)


@pytest.mark.parametrize("llegar_a", ["LISTO", "CERRADO", "CANCELADO"])
def test_no_se_cancela_en_estados_finales_o_listo(llegar_a):  # RN-08, INV-P8
    p = pedido_con_lineas(1)
    if llegar_a == "CANCELADO":
        p.cancelar("x", "enc", T0)
    else:
        p.confirmar("ana", CLIENTE, T0)
        p.iniciar_preparacion_de_linea(1, "chef", T0)
        p.marcar_linea_lista(1, "chef", T0)
        if llegar_a == "CERRADO":
            p.cerrar("ana", T0)
    with pytest.raises(CancelacionNoPermitida):
        p.cancelar("tarde", "enc", T0)


def test_se_cancela_en_preparacion():
    p = pedido_con_lineas(1)
    p.confirmar("ana", CLIENTE, T0)
    p.iniciar_preparacion_de_linea(1, "chef", T0)
    assert p.cancelar("falta de gas", "enc", T0) is EstadoPedido.EN_PREPARACION


def test_historial_solo_crece_y_conserva_orden():  # RN-09, INV-P7
    p = pedido_con_lineas(1)
    p.confirmar("ana", CLIENTE, T0)
    acciones = [h.accion for h in p.historial]
    assert acciones == ["Pedido iniciado", "Línea agregada", "Pedido autorizado", "Pedido confirmado"]
