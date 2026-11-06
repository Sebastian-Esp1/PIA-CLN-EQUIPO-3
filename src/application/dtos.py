"""DTO de lectura y respuesta: no exponen Aggregates (informe U3, Tabla 38)."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass
class LineaDto:
    linea_id: int
    producto_id: str
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal
    estacion: str
    estado_preparacion: str
    modificaciones: list = field(default_factory=list)


@dataclass
class PedidoDto:
    pedido_id: str
    canal: str
    cliente_id: str
    estado: str
    autorizado: bool
    promocion_id: str | None
    beneficio_aplicado: bool
    total: Decimal
    descuento: Decimal
    total_a_pagar: Decimal
    lineas: list
    cancelacion: dict | None = None


@dataclass
class ResultadoAgregarProducto:
    agregado: bool
    motivo: str
    pedido: PedidoDto


@dataclass
class ResultadoMarcarLista:
    pedido_listo: bool
    pedido: PedidoDto


@dataclass
class IngredienteDto:
    ingrediente_id: str
    nombre: str
    existencia: Decimal
    umbral: Decimal
    es_critico: bool


@dataclass
class DisponibilidadProductoDto:
    producto_id: str
    nombre: str
    disponible: bool
    motivo: str


@dataclass
class OrdenEstacionDto:
    pedido_id: str
    canal: str
    linea_id: int
    producto: str
    cantidad: int
    modificaciones: list
    estado_preparacion: str


@dataclass
class HistorialPedidoItemDto:
    accion: str
    usuario: str
    fecha: datetime
    detalle: str


@dataclass
class VentaResumenDto:
    pedido_id: str
    canal: str
    fecha_cierre: datetime
    total_productos: int
    total_importe: Decimal


@dataclass
class ComparativoInventarioDto:
    ingrediente_id: str
    ingrediente: str
    existencia_esperada: Decimal
    existencia_registrada: Decimal
    diferencia: Decimal


@dataclass
class IngredienteCriticoDto:
    ingrediente_id: str
    ingrediente: str
    existencia: Decimal
    umbral: Decimal
    productos_afectados: list
