"""Value Objects del dominio (informe U3, Tabla 18). Todos son inmutables."""

from dataclasses import dataclass
from datetime import datetime, time
from decimal import Decimal
from enum import Enum

from src.domain.errors import DatoInvalido


class CanalVenta(str, Enum):
    MESA = "MESA"
    TELEFONO = "TELEFONO"
    WHATSAPP = "WHATSAPP"
    DOMICILIO = "DOMICILIO"


class EstacionCocina(str, Enum):
    PARRILLA = "PARRILLA"
    PREPARACION_FRIA = "PREPARACION_FRIA"
    BEBIDAS = "BEBIDAS"
    EMPAQUE = "EMPAQUE"


class EstadoPreparacion(str, Enum):
    PENDIENTE = "PENDIENTE"
    EN_PREPARACION = "EN_PREPARACION"
    LISTA = "LISTA"


class TipoModificacion(str, Enum):
    QUITAR = "QUITAR"
    CAMBIAR = "CAMBIAR"
    AGREGAR = "AGREGAR"  # extra


class TipoMovimiento(str, Enum):
    ENTRADA = "ENTRADA"
    SALIDA = "SALIDA"
    CONTEO = "CONTEO"


def a_decimal(valor, nombre="valor"):
    """Convierte a Decimal rechazando bool, None y textos no numéricos."""
    if isinstance(valor, bool) or valor is None:
        raise DatoInvalido(f"{nombre} debe ser numérico")
    try:
        return Decimal(str(valor))
    except Exception as exc:  # noqa: BLE001 - se traduce a error de negocio
        raise DatoInvalido(f"{nombre} debe ser numérico") from exc


@dataclass(frozen=True)
class Modificacion:
    """Cambio o extra asociado a una línea del pedido (RN-03)."""

    tipo: TipoModificacion
    descripcion: str

    def __post_init__(self):
        if not isinstance(self.descripcion, str) or not self.descripcion.strip():
            raise DatoInvalido("La modificación necesita una descripción")


@dataclass(frozen=True)
class Cancelacion:
    """Motivo, usuario, fecha y hora de una cancelación (RN-07)."""

    motivo: str
    usuario: str
    fecha: datetime


@dataclass(frozen=True)
class RegistroDeCambio:
    """Entrada inmutable del historial de un pedido (RN-09)."""

    accion: str
    usuario: str
    fecha: datetime
    detalle: str = ""


@dataclass(frozen=True)
class Disponibilidad:
    """Resultado del cálculo de disponibilidad (RN-02, RN-12)."""

    disponible: bool
    motivo: str = ""

    @classmethod
    def si(cls):
        return cls(True, "")

    @classmethod
    def no(cls, motivo):
        return cls(False, motivo)


@dataclass(frozen=True)
class RequerimientoIngrediente:
    """Una línea de la receta: ingrediente y cantidad por unidad de producto."""

    ingrediente_id: str
    cantidad: Decimal

    def __post_init__(self):
        if a_decimal(self.cantidad, "cantidad") <= 0:
            raise DatoInvalido("La cantidad de la receta debe ser mayor a cero")


@dataclass(frozen=True)
class UmbralCritico:
    """Cantidad mínima a partir de la cual un ingrediente es crítico (SP-03)."""

    cantidad: Decimal

    def __post_init__(self):
        if a_decimal(self.cantidad, "umbral") < 0:
            raise DatoInvalido("El umbral no puede ser negativo")


@dataclass(frozen=True)
class MovimientoInventario:
    """Hecho histórico: solo se agrega, nunca se edita (RN-10)."""

    tipo: TipoMovimiento
    delta: Decimal
    existencia_resultante: Decimal
    usuario: str
    fecha: datetime
    referencia: str = ""


@dataclass(frozen=True)
class VentanaHoraria:
    """Horario de una promoción: inicio menor a fin (INV-M1)."""

    inicio: time
    fin: time

    def __post_init__(self):
        if not self.inicio < self.fin:
            raise DatoInvalido("La ventana horaria necesita inicio menor que fin")

    def contiene(self, momento: datetime) -> bool:
        return self.inicio <= momento.time() <= self.fin
