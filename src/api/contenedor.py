"""Raíz de composición: conecta puertos con implementaciones (inversión de dependencias)."""

import uuid
from dataclasses import dataclass

from src.application.queries import Consultas
from src.application.servicios import (
    ServicioDeCatalogo,
    ServicioDeCocina,
    ServicioDeInventario,
    ServicioDePedidos,
    ServicioDePromociones,
)
from src.infrastructure.base_de_datos import (
    crear_fabrica_de_sesiones,
    crear_motor,
    crear_tablas,
)
from src.infrastructure.config import Configuracion
from src.infrastructure.consultas import (
    ConsultasDeInventarioSql,
    ConsultasDePedidosSql,
    ConsultasDeVentasSql,
)
from src.infrastructure.seguridad import AutorizadorPorRol
from src.infrastructure.unidad_de_trabajo import (
    ActualizadorDeVentas,
    PublicadorEnMemoria,
    RelojDelSistema,
    UnidadDeTrabajoSql,
)


def generar_id_de_pedido() -> str:
    return f"PED-{uuid.uuid4().hex[:8].upper()}"


@dataclass
class Contenedor:
    configuracion: Configuracion
    motor: object
    fabrica_de_sesiones: object
    uow_factory: object
    reloj: object
    pedidos: ServicioDePedidos
    cocina: ServicioDeCocina
    inventario: ServicioDeInventario
    catalogo: ServicioDeCatalogo
    promociones: ServicioDePromociones
    consultas: Consultas


def construir_contenedor(configuracion: Configuracion | None = None, reloj=None) -> Contenedor:
    cfg = configuracion or Configuracion.desde_entorno()
    motor = crear_motor(cfg.database_url)
    crear_tablas(motor)
    fabrica = crear_fabrica_de_sesiones(motor)
    publicador = PublicadorEnMemoria()
    publicador.suscribir("PedidoCerrado", ActualizadorDeVentas(fabrica))
    reloj = reloj or RelojDelSistema(cfg.app_timezone)
    autorizador = AutorizadorPorRol()

    def uow_factory():
        return UnidadDeTrabajoSql(fabrica, publicador)

    return Contenedor(
        configuracion=cfg,
        motor=motor,
        fabrica_de_sesiones=fabrica,
        uow_factory=uow_factory,
        reloj=reloj,
        pedidos=ServicioDePedidos(uow_factory, reloj, autorizador, generar_id_de_pedido),
        cocina=ServicioDeCocina(uow_factory, reloj, autorizador),
        inventario=ServicioDeInventario(uow_factory, reloj, autorizador),
        catalogo=ServicioDeCatalogo(uow_factory, reloj, autorizador),
        promociones=ServicioDePromociones(uow_factory, reloj, autorizador),
        consultas=Consultas(
            ConsultasDePedidosSql(fabrica),
            ConsultasDeInventarioSql(fabrica),
            ConsultasDeVentasSql(fabrica),
            autorizador,
        ),
    )
