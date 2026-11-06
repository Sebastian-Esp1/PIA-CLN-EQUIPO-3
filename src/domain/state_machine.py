"""State Machine del pedido (SP-01, SP-02, RN-08).

Las reglas de qué transiciones, modificaciones y cancelaciones permite cada estado viven aquí
y solo aquí: ningún servicio ni endpoint decide por su cuenta (hallazgo SOLID-04).
"""

from collections.abc import Mapping
from enum import Enum
from typing import Generic, TypeVar

from src.domain.errors import TransicionDeEstadoInvalida

E = TypeVar("E", bound=Enum)


class MaquinaDeEstados(Generic[E]):  # noqa: UP046 - se mantiene compatible con Python 3.11
    """Tabla de transiciones permitidas, reutilizable para cualquier Enum."""

    def __init__(self, transiciones: Mapping[E, frozenset]):
        self._transiciones = dict(transiciones)

    def destinos(self, origen: E) -> frozenset:
        return self._transiciones.get(origen, frozenset())

    def puede(self, origen: E, destino: E) -> bool:
        return destino in self.destinos(origen)

    def validar(self, origen: E, destino: E) -> None:
        if not self.puede(origen, destino):
            raise TransicionDeEstadoInvalida(
                f"El pedido no puede pasar de {origen.value} a {destino.value}."
            )


class EstadoPedido(str, Enum):
    EN_REGISTRO = "EN_REGISTRO"  # CREADO en el paquete del docente
    CONFIRMADO = "CONFIRMADO"  # ACEPTADO en el paquete del docente
    EN_PREPARACION = "EN_PREPARACION"
    LISTO = "LISTO"
    CERRADO = "CERRADO"  # ENTREGADO en el paquete del docente
    CANCELADO = "CANCELADO"

    @property
    def permite_modificar(self) -> bool:
        """SP-02: solo se modifica en EnRegistro y Confirmado."""
        return self in (EstadoPedido.EN_REGISTRO, EstadoPedido.CONFIRMADO)

    @property
    def permite_cancelar(self) -> bool:
        """SP-02: se cancela en EnRegistro, Confirmado y EnPreparacion."""
        return self in (
            EstadoPedido.EN_REGISTRO,
            EstadoPedido.CONFIRMADO,
            EstadoPedido.EN_PREPARACION,
        )

    @property
    def es_final(self) -> bool:
        return self in (EstadoPedido.CERRADO, EstadoPedido.CANCELADO)


MAQUINA_PEDIDO = MaquinaDeEstados[EstadoPedido](
    {
        EstadoPedido.EN_REGISTRO: frozenset({EstadoPedido.CONFIRMADO, EstadoPedido.CANCELADO}),
        EstadoPedido.CONFIRMADO: frozenset({EstadoPedido.EN_PREPARACION, EstadoPedido.CANCELADO}),
        EstadoPedido.EN_PREPARACION: frozenset({EstadoPedido.LISTO, EstadoPedido.CANCELADO}),
        EstadoPedido.LISTO: frozenset({EstadoPedido.CERRADO}),
        EstadoPedido.CERRADO: frozenset(),
        EstadoPedido.CANCELADO: frozenset(),
    }
)
