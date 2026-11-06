"""Patrón Specification con composición AND / OR / NOT.

Cada Specification responde una pregunta de negocio sobre una `EvaluacionPedido`. Se componen con
los operadores `&`, `|` y `~`, y explican por qué fallaron (`motivos_de_fallo`).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from src.domain.value_objects import CanalVenta, VentanaHoraria


@dataclass(frozen=True)
class EvaluacionPedido:
    """Lo que las Specifications necesitan conocer: el pedido, su cliente y el momento."""

    pedido: object
    cliente: object
    momento: datetime


class Specification(ABC):
    descripcion = "condición"

    @abstractmethod
    def es_satisfecha_por(self, candidato) -> bool: ...

    def motivos_de_fallo(self, candidato) -> list:
        """Hojas que no se cumplen; vacío si la especificación se satisface."""
        return [] if self.es_satisfecha_por(candidato) else [self.descripcion]

    def __and__(self, otra):
        return Y(self, otra)

    def __or__(self, otra):
        return O(self, otra)

    def __invert__(self):
        return No(self)


class Y(Specification):
    def __init__(self, izquierda, derecha):
        self.izquierda, self.derecha = izquierda, derecha
        self.descripcion = f"({izquierda.descripcion} Y {derecha.descripcion})"

    def es_satisfecha_por(self, candidato):
        return self.izquierda.es_satisfecha_por(candidato) and self.derecha.es_satisfecha_por(
            candidato
        )

    def motivos_de_fallo(self, candidato):
        return self.izquierda.motivos_de_fallo(candidato) + self.derecha.motivos_de_fallo(candidato)


class O(Specification):  # noqa: E742 - nombre de dominio: operador lógico OR
    def __init__(self, izquierda, derecha):
        self.izquierda, self.derecha = izquierda, derecha
        self.descripcion = f"({izquierda.descripcion} O {derecha.descripcion})"

    def es_satisfecha_por(self, candidato):
        return self.izquierda.es_satisfecha_por(candidato) or self.derecha.es_satisfecha_por(
            candidato
        )


class No(Specification):
    def __init__(self, especificacion):
        self.especificacion = especificacion
        self.descripcion = f"NO {especificacion.descripcion}"

    def es_satisfecha_por(self, candidato):
        return not self.especificacion.es_satisfecha_por(candidato)


# --- Especificaciones simples ---------------------------------------------------------------
class ClienteActivo(Specification):
    descripcion = "el cliente debe estar activo"

    def es_satisfecha_por(self, c):
        return bool(c.cliente.activo)


class ClientePreferente(Specification):
    descripcion = "el cliente debe ser preferente"

    def es_satisfecha_por(self, c):
        return bool(c.cliente.es_preferente)


class PedidoConLineas(Specification):
    descripcion = "el pedido debe tener al menos una línea"

    def es_satisfecha_por(self, c):
        return len(c.pedido.lineas) >= 1


class PedidoAutorizado(Specification):
    descripcion = "el pedido debe estar autorizado"

    def es_satisfecha_por(self, c):
        return bool(c.pedido.autorizado)


class TotalMinimo(Specification):
    def __init__(self, monto):
        self.monto = Decimal(str(monto))
        self.descripcion = f"el total debe ser de al menos {self.monto} MXN"

    def es_satisfecha_por(self, c):
        return c.pedido.total >= self.monto


class TienePromocionActiva(Specification):
    descripcion = "el pedido tiene una promoción activa"

    def es_satisfecha_por(self, c):
        return c.pedido.promocion_activa


class CanalEn(Specification):
    def __init__(self, *canales):
        self.canales = frozenset(CanalVenta(canal) for canal in canales)
        self.descripcion = "el canal debe ser " + " o ".join(sorted(x.value for x in self.canales))

    def es_satisfecha_por(self, c):
        return c.pedido.canal in self.canales


class DentroDeVentana(Specification):
    def __init__(self, ventana: VentanaHoraria):
        self.ventana = ventana
        self.descripcion = f"estar entre {ventana.inicio:%H:%M} y {ventana.fin:%H:%M}"

    def es_satisfecha_por(self, c):
        return self.ventana.contiene(c.momento)


# --- Reglas compuestas del negocio ------------------------------------------------------------
UMBRAL_BENEFICIO_MXN = Decimal("1500")


def puede_procesarse() -> Specification:
    """R1 del paquete del docente: cliente activo Y con líneas Y autorizado."""
    return ClienteActivo() & PedidoConLineas() & PedidoAutorizado()


def califica_beneficio() -> Specification:
    """R2 del paquete del docente: preferente Y total >= 1500 Y NO promoción activa."""
    return ClientePreferente() & TotalMinimo(UMBRAL_BENEFICIO_MXN) & ~TienePromocionActiva()
