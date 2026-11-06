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
def _modelo(ejemplo: dict, desde_atributos: bool = True) -> ConfigDict:
    """Configuración con un ejemplo realista que Swagger muestra en lugar de "string"."""
    return ConfigDict(from_attributes=desde_atributos, json_schema_extra={"examples": [ejemplo]})


class ModificacionOut(BaseModel):
    model_config = _modelo({"tipo": "QUITAR", "descripcion": "Sin cebolla"})
    tipo: str = Field(description="Qué se hace: QUITAR, CAMBIAR o AGREGAR")
    descripcion: str = Field(description="Indicación para cocina")


_LINEA_EJ = {
    "linea_id": 1,
    "producto_id": "PED-P001",
    "cantidad": 2,
    "precio_unitario": "290.00",
    "subtotal": "580.00",
    "estacion": "PARRILLA",
    "estado_preparacion": "PENDIENTE",
    "modificaciones": [{"tipo": "QUITAR", "descripcion": "Sin cebolla"}],
}


class LineaOut(BaseModel):
    model_config = _modelo(_LINEA_EJ)
    linea_id: int = Field(description="Número de la línea dentro del pedido")
    producto_id: str = Field(description="Código del platillo o bebida")
    cantidad: int = Field(description="Piezas pedidas")
    precio_unitario: Decimal = Field(description="Precio de una pieza, en pesos")
    subtotal: Decimal = Field(description="Cantidad por precio, en pesos")
    estacion: str = Field(description="Dónde se prepara: PARRILLA, PREPARACION_FRIA, BEBIDAS o EMPAQUE")
    estado_preparacion: str = Field(description="PENDIENTE, EN_PREPARACION o LISTA")
    modificaciones: list[ModificacionOut] = Field(description="Cambios o extras pedidos por el cliente")


class CancelacionOut(BaseModel):
    model_config = _modelo(
        {"motivo": "El cliente cambió de opinión", "usuario": "ana", "fecha": "2026-11-06T13:20:00"}
    )
    motivo: str = Field(description="Razón escrita por quien canceló")
    usuario: str = Field(description="Quién canceló")
    fecha: datetime = Field(description="Cuándo se canceló")


_PEDIDO_EJ = {
    "pedido_id": "PED-O0001",
    "canal": "MESA",
    "cliente_id": "PED-C001",
    "estado": "EN_REGISTRO",
    "autorizado": False,
    "promocion_id": None,
    "beneficio_aplicado": False,
    "total": "580.00",
    "descuento": "0.00",
    "total_a_pagar": "580.00",
    "lineas": [_LINEA_EJ],
    "cancelacion": None,
}


class PedidoOut(BaseModel):
    model_config = _modelo(_PEDIDO_EJ)
    pedido_id: str = Field(description="Número del pedido")
    canal: str = Field(description="Por dónde llegó: MESA, TELEFONO, WHATSAPP o DOMICILIO")
    cliente_id: str = Field(description="Código del cliente")
    estado: str = Field(
        description="En qué etapa va: EN_REGISTRO, CONFIRMADO, EN_PREPARACION, LISTO, CERRADO o CANCELADO"
    )
    autorizado: bool = Field(description="Si ya fue autorizado para confirmarse")
    promocion_id: str | None = Field(description="Promoción aplicada, si hubo")
    beneficio_aplicado: bool = Field(description="Si el cliente recibió algún beneficio")
    total: Decimal = Field(description="Suma de las líneas, en pesos")
    descuento: Decimal = Field(description="Descuento aplicado, en pesos")
    total_a_pagar: Decimal = Field(description="Lo que paga el cliente, en pesos")
    lineas: list[LineaOut] = Field(description="Productos del pedido")
    cancelacion: CancelacionOut | None = Field(default=None, description="Datos de la cancelación, si se canceló")


class LineaAgregadaOut(BaseModel):
    model_config = _modelo(
        {"agregado": True, "motivo": "Producto agregado al pedido", "pedido": _PEDIDO_EJ}
    )
    agregado: bool = Field(description="Si el producto se pudo agregar")
    motivo: str = Field(description="Explicación en palabras del resultado")
    pedido: PedidoOut = Field(description="El pedido tal como quedó")


class LineaListaOut(BaseModel):
    model_config = _modelo({"pedido_listo": False, "pedido": _PEDIDO_EJ})
    pedido_listo: bool = Field(description="Verdadero cuando todas las líneas ya están listas")
    pedido: PedidoOut = Field(description="El pedido tal como quedó")


class HistorialOut(BaseModel):
    model_config = _modelo(
        {
            "accion": "CONFIRMAR",
            "usuario": "ana",
            "fecha": "2026-11-06T13:15:00",
            "detalle": "Pedido confirmado y enviado a cocina",
        }
    )
    accion: str = Field(description="Qué se hizo")
    usuario: str = Field(description="Quién lo hizo")
    fecha: datetime = Field(description="Cuándo ocurrió")
    detalle: str = Field(description="Explicación del cambio")


class OrdenEstacionOut(BaseModel):
    model_config = _modelo(
        {
            "pedido_id": "PED-O0001",
            "canal": "MESA",
            "linea_id": 1,
            "producto": "Hamburguesa 01",
            "cantidad": 2,
            "modificaciones": [{"tipo": "QUITAR", "descripcion": "Sin cebolla"}],
            "estado_preparacion": "PENDIENTE",
        }
    )
    pedido_id: str = Field(description="Pedido al que pertenece")
    canal: str = Field(description="Por dónde llegó el pedido")
    linea_id: int = Field(description="Línea del pedido")
    producto: str = Field(description="Nombre del platillo o bebida")
    cantidad: int = Field(description="Piezas a preparar")
    modificaciones: list[ModificacionOut] = Field(description="Indicaciones especiales")
    estado_preparacion: str = Field(description="PENDIENTE, EN_PREPARACION o LISTA")


class DisponibilidadOut(BaseModel):
    model_config = _modelo(
        {
            "producto_id": "PED-P001",
            "nombre": "Hamburguesa 01",
            "disponible": True,
            "motivo": "Disponible",
        }
    )
    producto_id: str = Field(description="Código del producto")
    nombre: str = Field(description="Nombre del producto")
    disponible: bool = Field(description="Si se puede vender ahora")
    motivo: str = Field(description="Por qué está o no disponible")


class IngredienteOut(BaseModel):
    model_config = _modelo(
        {
            "ingrediente_id": "ING-PED-P001",
            "nombre": "Insumo base de Hamburguesa 01",
            "existencia": "13.000",
            "umbral": "3.000",
            "es_critico": False,
        }
    )
    ingrediente_id: str = Field(description="Código del ingrediente")
    nombre: str = Field(description="Nombre del ingrediente")
    existencia: Decimal = Field(description="Cuánto hay en bodega ahora")
    umbral: Decimal = Field(description="Cantidad mínima antes de considerarlo en riesgo")
    es_critico: bool = Field(description="Verdadero si ya está en o por debajo del mínimo")


class CriticoOut(BaseModel):
    model_config = _modelo(
        {
            "ingrediente_id": "ING-PED-P001",
            "ingrediente": "Insumo base de Hamburguesa 01",
            "existencia": "2.000",
            "umbral": "3.000",
            "productos_afectados": ["PED-P001", "PED-P005"],
        },
        desde_atributos=True,
    )
    ingrediente_id: str = Field(description="Código del ingrediente")
    ingrediente: str = Field(description="Nombre del ingrediente")
    existencia: Decimal = Field(description="Cuánto queda")
    umbral: Decimal = Field(description="Mínimo recomendado")
    productos_afectados: list[str] = Field(description="Productos que se dejarían de poder vender")


class VentaOut(BaseModel):
    model_config = _modelo(
        {
            "pedido_id": "PED-O0001",
            "canal": "MESA",
            "fecha_cierre": "2026-11-06T14:00:00",
            "total_productos": 3,
            "total_importe": "870.00",
        }
    )
    pedido_id: str = Field(description="Pedido vendido")
    canal: str = Field(description="Por dónde se vendió")
    fecha_cierre: datetime = Field(description="Cuándo se entregó")
    total_productos: int = Field(description="Piezas vendidas")
    total_importe: Decimal = Field(description="Importe cobrado, en pesos")


class ComparativoOut(BaseModel):
    model_config = _modelo(
        {
            "ingrediente_id": "ING-PED-P001",
            "ingrediente": "Insumo base de Hamburguesa 01",
            "existencia_esperada": "20.000",
            "existencia_registrada": "18.500",
            "diferencia": "-1.500",
        }
    )
    ingrediente_id: str = Field(description="Código del ingrediente")
    ingrediente: str = Field(description="Nombre del ingrediente")
    existencia_esperada: Decimal = Field(description="Lo que debería haber según las ventas")
    existencia_registrada: Decimal = Field(description="Lo que se contó realmente")
    diferencia: Decimal = Field(description="Registrado menos esperado; negativo significa faltante")


class ProductoEstadoOut(BaseModel):
    model_config = _modelo({"producto_id": "PED-P011", "agotado": True}, desde_atributos=False)
    producto_id: str = Field(description="Código del producto")
    agotado: bool = Field(description="Si quedó marcado como agotado")


class PromocionOut(BaseModel):
    model_config = _modelo({"promocion_id": "PROMO-HAPPY", "vigente": True}, desde_atributos=False)
    promocion_id: str = Field(description="Código de la promoción")
    vigente: bool = Field(description="Si está activa en este momento")


class ImportacionOut(BaseModel):
    model_config = _modelo(
        {"clientes": 20, "productos": 20, "pedidos": 40, "lineas": 120}, desde_atributos=False
    )
    clientes: int = Field(description="Clientes cargados")
    productos: int = Field(description="Productos cargados")
    pedidos: int = Field(description="Pedidos cargados")
    lineas: int = Field(description="Líneas de pedido cargadas")
