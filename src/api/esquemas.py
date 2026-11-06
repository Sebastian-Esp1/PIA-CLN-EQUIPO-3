"""Esquemas Pydantic de la API REST (contrato OpenAPI)."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class _Salida(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ErrorOut(BaseModel):
    codigo: str = Field(examples=["PEDIDO_NO_PROCESABLE"])
    mensaje: str = Field(examples=["El pedido no puede procesarse: el cliente debe estar activo."])


# --- entrada ---
class PedidoIn(BaseModel):
    canal: str = Field(examples=["MESA"], description="MESA, TELEFONO, WHATSAPP o DOMICILIO")
    cliente_id: str = Field(examples=["PED-C001"])


class LineaIn(BaseModel):
    producto_id: str = Field(examples=["PED-P001"])
    cantidad: int = Field(examples=[2], description="Entero mayor a cero")


class ModificacionIn(BaseModel):
    tipo: str = Field(examples=["QUITAR"], description="QUITAR, CAMBIAR o AGREGAR")
    descripcion: str = Field(examples=["Sin cebolla"])


class CancelacionIn(BaseModel):
    motivo: str = Field(examples=["El cliente cambió de opinión"])


class MovimientoIn(BaseModel):
    tipo: str = Field(examples=["ENTRADA"], description="ENTRADA o SALIDA")
    cantidad: Decimal = Field(examples=["10"])


class ConteoIn(BaseModel):
    cantidad_contada: Decimal = Field(examples=["25"])


class UmbralIn(BaseModel):
    umbral: Decimal = Field(examples=["5"])


class PromocionIn(BaseModel):
    promocion_id: str = Field(examples=["PROMO-HAPPY"])
    nombre: str = Field(examples=["Happy hour"])
    hora_inicio: str = Field(examples=["16:00"])
    hora_fin: str = Field(examples=["19:00"])
    total_minimo: Decimal | None = Field(default=None, examples=["300"])
    canales: list[str] = Field(default_factory=list, examples=[["MESA"]])
    descuento_pct: Decimal = Field(default=Decimal("10"), examples=["10"])


# --- salida ---
class ModificacionOut(_Salida):
    tipo: str
    descripcion: str


class LineaOut(_Salida):
    linea_id: int
    producto_id: str
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal
    estacion: str
    estado_preparacion: str
    modificaciones: list[ModificacionOut]


class CancelacionOut(_Salida):
    motivo: str
    usuario: str
    fecha: datetime


class PedidoOut(_Salida):
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
    lineas: list[LineaOut]
    cancelacion: CancelacionOut | None = None


class LineaAgregadaOut(_Salida):
    agregado: bool
    motivo: str
    pedido: PedidoOut


class LineaListaOut(_Salida):
    pedido_listo: bool
    pedido: PedidoOut


class HistorialOut(_Salida):
    accion: str
    usuario: str
    fecha: datetime
    detalle: str


class OrdenEstacionOut(_Salida):
    pedido_id: str
    canal: str
    linea_id: int
    producto: str
    cantidad: int
    modificaciones: list[ModificacionOut]
    estado_preparacion: str


class DisponibilidadOut(_Salida):
    producto_id: str
    nombre: str
    disponible: bool
    motivo: str


class IngredienteOut(_Salida):
    ingrediente_id: str
    nombre: str
    existencia: Decimal
    umbral: Decimal
    es_critico: bool


class CriticoOut(_Salida):
    ingrediente_id: str
    ingrediente: str
    existencia: Decimal
    umbral: Decimal
    productos_afectados: list[str]


class VentaOut(_Salida):
    pedido_id: str
    canal: str
    fecha_cierre: datetime
    total_productos: int
    total_importe: Decimal


class ComparativoOut(_Salida):
    ingrediente_id: str
    ingrediente: str
    existencia_esperada: Decimal
    existencia_registrada: Decimal
    diferencia: Decimal


class ProductoEstadoOut(BaseModel):
    producto_id: str
    agotado: bool


class PromocionOut(BaseModel):
    promocion_id: str
    vigente: bool


class ImportacionOut(BaseModel):
    clientes: int
    productos: int
    pedidos: int
    lineas: int
