"""Domain Events: hechos que ya ocurrieron (informe U3, Tabla 21)."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class EventoDeDominio:
    ocurrido_en: datetime
    agregado_id: str
    usuario: str = ""
    detalle: dict = field(default_factory=dict)

    @property
    def nombre(self) -> str:
        return type(self).__name__


class PedidoIniciado(EventoDeDominio): ...


class PedidoAutorizado(EventoDeDominio): ...


class PedidoConfirmado(EventoDeDominio): ...


class ModificacionAgregada(EventoDeDominio): ...


class ProductoRechazadoPorDisponibilidad(EventoDeDominio): ...


class LineaPreparada(EventoDeDominio): ...


class PedidoListo(EventoDeDominio): ...


class PedidoCerrado(EventoDeDominio): ...


class PedidoCancelado(EventoDeDominio): ...


class PromocionAplicada(EventoDeDominio): ...


class BeneficioPreferenteAplicado(EventoDeDominio): ...


class ExistenciaActualizada(EventoDeDominio): ...


class IngredienteMarcadoCritico(EventoDeDominio): ...


class ProductoMarcadoAgotado(EventoDeDominio): ...


class ProductoReactivado(EventoDeDominio): ...
