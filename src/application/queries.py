"""Lado de lectura de CQRS (ADR-04): Queries que devuelven DTO sin cargar Aggregates."""

from datetime import datetime

from src.application.ports import (
    Accion,
    IAutorizador,
    IConsultasDeInventario,
    IConsultasDePedidos,
    IConsultasDeVentas,
    Usuario,
)
from src.domain.errors import DatoInvalido, NoAutorizado, RecursoNoEncontrado
from src.domain.value_objects import EstacionCocina


class Consultas:
    def __init__(
        self,
        pedidos: IConsultasDePedidos,
        inventario: IConsultasDeInventario,
        ventas: IConsultasDeVentas,
        autorizador: IAutorizador,
    ):
        self._pedidos, self._inventario, self._ventas = pedidos, inventario, ventas
        self._autorizador = autorizador

    def _exigir(self, usuario: Usuario, accion: Accion):
        if not self._autorizador.puede(usuario, accion):
            raise NoAutorizado(f"El rol {usuario.rol.value} no puede realizar {accion.value}.")

    # Queries del proceso principal
    def consultar_pedido(self, pedido_id):
        pedido = self._pedidos.obtener(pedido_id)
        if pedido is None:
            raise RecursoNoEncontrado(f"El pedido {pedido_id} no existe.")
        return pedido

    def listar_pedidos(self, estado=None, limite=50):
        return self._pedidos.listar(estado, limite)

    def consultar_ordenes_de_estacion(self, estacion: str):  # US-07
        try:
            estacion = EstacionCocina(estacion)
        except ValueError as exc:
            raise DatoInvalido("La estación debe ser PARRILLA, PREPARACION_FRIA, BEBIDAS o EMPAQUE") from exc
        return self._pedidos.ordenes_de_estacion(estacion)

    def consultar_historial_de_pedido(self, pedido_id):  # US-12
        self.consultar_pedido(pedido_id)
        return self._pedidos.historial(pedido_id)

    def consultar_disponibilidad_de_productos(self):  # US-04
        return self._inventario.disponibilidad_de_productos()

    def consultar_ingredientes(self):
        return self._inventario.ingredientes()

    def consultar_ingredientes_criticos(self):  # US-10
        return self._inventario.ingredientes_criticos()

    def consultar_ventas_por_periodo(self, usuario: Usuario, desde: datetime, hasta: datetime):
        self._exigir(usuario, Accion.CONSULTAR_REPORTES)  # US-13
        return self._ventas.ventas_por_periodo(desde, hasta)

    def consultar_comparativo_ventas_inventario(self, usuario, desde, hasta):  # US-14
        self._exigir(usuario, Accion.CONSULTAR_REPORTES)
        return self._inventario.comparativo(desde, hasta)
