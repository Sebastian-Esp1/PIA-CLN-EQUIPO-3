"""Commands: intenciones de cambio de estado (CQRS básico, ADR-04)."""

from dataclasses import dataclass, field
from decimal import Decimal

from src.application.ports import Usuario


@dataclass(frozen=True)
class IniciarPedido:
    canal: str
    cliente_id: str
    usuario: Usuario


@dataclass(frozen=True)
class AgregarProductoAlPedido:
    pedido_id: str
    producto_id: str
    cantidad: int
    usuario: Usuario


@dataclass(frozen=True)
class AgregarModificacion:
    pedido_id: str
    linea_id: int
    tipo: str
    descripcion: str
    usuario: Usuario


@dataclass(frozen=True)
class AutorizarPedido:
    pedido_id: str
    usuario: Usuario


@dataclass(frozen=True)
class ConfirmarPedido:
    pedido_id: str
    usuario: Usuario


@dataclass(frozen=True)
class CancelarPedido:
    pedido_id: str
    motivo: str
    usuario: Usuario


@dataclass(frozen=True)
class CerrarPedido:
    pedido_id: str
    usuario: Usuario


@dataclass(frozen=True)
class IniciarPreparacion:
    pedido_id: str
    linea_id: int
    usuario: Usuario


@dataclass(frozen=True)
class MarcarLineaLista:
    pedido_id: str
    linea_id: int
    usuario: Usuario


@dataclass(frozen=True)
class RegistrarExistencia:
    ingrediente_id: str
    cantidad_contada: Decimal
    usuario: Usuario


@dataclass(frozen=True)
class RegistrarMovimiento:
    ingrediente_id: str
    tipo: str
    cantidad: Decimal
    usuario: Usuario


@dataclass(frozen=True)
class DefinirUmbralCritico:
    ingrediente_id: str
    umbral: Decimal
    usuario: Usuario


@dataclass(frozen=True)
class CambiarEstadoDeProducto:
    producto_id: str
    usuario: Usuario


@dataclass(frozen=True)
class ConfigurarPromocion:
    promocion_id: str
    nombre: str
    hora_inicio: str
    hora_fin: str
    total_minimo: Decimal | None
    canales: list = field(default_factory=list)
    descuento_pct: Decimal = Decimal("0")
    usuario: Usuario | None = None
