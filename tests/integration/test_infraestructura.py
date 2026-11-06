"""Persistencia: concurrencia optimista, rollback atómico, eventos, configuración 12-Factor."""

from datetime import datetime
from decimal import Decimal

import pytest

from src.application import commands as cmd
from src.application.ports import Rol, Usuario
from src.domain.errors import ConflictoDeConcurrencia, ExistenciaInsuficiente
from src.infrastructure.base_de_datos import crear_motor
from src.infrastructure.config import Configuracion
from src.infrastructure.unidad_de_trabajo import PublicadorEnMemoria, RelojDelSistema

pytestmark = pytest.mark.integration
USR = Usuario("enc", Rol.ENCARGADO)


def crear_pedido(c, cliente="PED-C001"):
    return c.pedidos.iniciar_pedido(cmd.IniciarPedido("MESA", cliente, USR)).pedido_id


def test_concurrencia_optimista_rechaza_la_segunda_escritura_vieja(datos):
    pid = crear_pedido(datos)
    with datos.uow_factory() as a, datos.uow_factory() as b:
        pedido_a = a.pedidos.obtener_por_id(pid)
        pedido_b = b.pedidos.obtener_por_id(pid)
        pedido_a.autorizar("a", datetime(2026, 11, 5))
        a.pedidos.guardar(pedido_a)
        a.confirmar()
        pedido_b.autorizar("b", datetime(2026, 11, 5))
        with pytest.raises(ConflictoDeConcurrencia):
            b.pedidos.guardar(pedido_b)


def test_rollback_no_deja_cambios_parciales(datos):
    with pytest.raises(ExistenciaInsuficiente):
        with datos.uow_factory() as uow:
            ing = uow.ingredientes.obtener_por_id("ING-PED-P001")
            ing.registrar_salida(Decimal(1), "x", datetime(2026, 11, 5))
            uow.ingredientes.guardar(ing)
            ing.registrar_salida(Decimal(9999), "x", datetime(2026, 11, 5))
    with datos.uow_factory() as uow:
        assert uow.ingredientes.obtener_por_id("ING-PED-P001").existencia == Decimal(13)


def test_revertir_descarta_eventos_y_cambios(datos):
    with datos.uow_factory() as uow:
        ing = uow.ingredientes.obtener_por_id("ING-PED-P001")
        ing.registrar_entrada(Decimal(5), "x", datetime(2026, 11, 5))
        uow.ingredientes.guardar(ing)
        uow.registrar_eventos(ing.extraer_eventos())
        uow.revertir()
    with datos.uow_factory() as uow:
        assert uow.ingredientes.obtener_por_id("ING-PED-P001").existencia == Decimal(13)


def test_eventos_se_guardan_en_bitacora_y_se_publican_tras_el_commit(datos):
    recibidos = []
    pid = crear_pedido(datos)
    publicador = PublicadorEnMemoria()
    publicador.suscribir("PedidoIniciado", recibidos.append)
    publicador.publicar([])  # sin eventos no pasa nada
    from src.domain.events import PedidoIniciado

    publicador.publicar([PedidoIniciado(datetime(2026, 11, 5), pid, "x", {})])
    assert len(recibidos) == 1
    from sqlalchemy import select

    from src.infrastructure.modelos import EventoRow

    with datos.fabrica_de_sesiones() as s:
        nombres = [e.nombre for e in s.scalars(select(EventoRow).where(EventoRow.agregado_id == pid))]
    assert nombres == ["PedidoIniciado"]


def test_la_venta_se_registra_una_sola_vez(datos, reloj):
    from src.domain.events import PedidoCerrado
    from src.infrastructure.unidad_de_trabajo import ActualizadorDeVentas

    evento = PedidoCerrado(reloj.ahora(), "PED-O001", "x", {"total": "100", "unidades": 1, "canal": "MESA"})
    actualizador = ActualizadorDeVentas(datos.fabrica_de_sesiones)
    actualizador(evento)
    actualizador(evento)  # idempotente
    ventas = datos.consultas.consultar_ventas_por_periodo(USR, datetime(2026, 1, 1), datetime(2026, 12, 31))
    assert [v.pedido_id for v in ventas].count("PED-O001") == 1


def test_importacion_es_idempotente(datos):
    from src.infrastructure.importacion_csv import importar
    from tests.conftest import DATA

    assert importar(datos.uow_factory, DATA) == {"clientes": 0, "productos": 0, "pedidos": 0, "lineas": 0}


def test_repositorios_devuelven_none_o_vacio_si_no_existe(datos):
    with datos.uow_factory() as uow:
        assert uow.pedidos.obtener_por_id("X") is None
        assert uow.clientes.obtener_por_id("X") is None
        assert uow.productos.obtener_por_id("X") is None
        assert uow.ingredientes.obtener_por_id("X") is None
        assert uow.promociones.obtener_por_id("X") is None
        assert uow.productos.obtener_por_ids([]) == {}


def test_configuracion_lee_entorno_y_normaliza_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@host/db")
    monkeypatch.setenv("SEED_ON_START", "true")
    monkeypatch.setenv("API_KEY", "k")
    cfg = Configuracion.desde_entorno()
    assert cfg.database_url == "postgresql+psycopg2://u:p@host/db"
    assert cfg.seed_on_start and cfg.api_key == "k"
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@host/db")
    monkeypatch.delenv("SEED_ON_START")
    cfg = Configuracion.desde_entorno()
    assert cfg.database_url.startswith("postgresql+psycopg2://") and not cfg.seed_on_start


def test_motores_para_sqlite_archivo_y_reloj_con_zona(tmp_path):
    motor = crear_motor(f"sqlite:///{tmp_path / 'x.db'}")
    assert motor.dialect.name == "sqlite"
    motor.dispose()
    assert RelojDelSistema("America/Monterrey").ahora().year >= 2026


def test_punto_de_entrada_construye_la_app_desde_el_entorno(monkeypatch, tmp_path):
    import importlib

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'arranque.db'}")
    import src.api.principal as principal

    principal.app.state.contenedor.motor.dispose()  # la primera importación ya creó una app
    principal = importlib.reload(principal)
    try:
        assert principal.app.title.startswith("Sazón Urbano")
    finally:
        principal.app.state.contenedor.motor.dispose()
