"""Tablas SQLAlchemy (modelo de persistencia, separado del modelo de dominio)."""

import warnings
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# SQLite guarda los Numeric como punto flotante; los importes con 2 decimales se leen exactos.
warnings.filterwarnings("ignore", message=".*does \\*not\\* support Decimal objects natively.*")


class Base(DeclarativeBase):
    pass


class ClienteRow(Base):
    __tablename__ = "clientes"
    cliente_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    es_preferente: Mapped[bool] = mapped_column(Boolean, default=False)
    ciudad: Mapped[str] = mapped_column(String(80), default="")


class IngredienteRow(Base):
    __tablename__ = "ingredientes"
    ingrediente_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    unidad: Mapped[str] = mapped_column(String(20), default="pza")
    existencia: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    umbral: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    version: Mapped[int] = mapped_column(Integer, default=0)


class MovimientoRow(Base):
    __tablename__ = "movimientos_inventario"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ingrediente_id: Mapped[str] = mapped_column(ForeignKey("ingredientes.ingrediente_id"), index=True)
    tipo: Mapped[str] = mapped_column(String(10))
    delta: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    existencia_resultante: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    usuario: Mapped[str] = mapped_column(String(60))
    fecha: Mapped[datetime] = mapped_column(DateTime)
    referencia: Mapped[str] = mapped_column(String(120), default="")


class ProductoRow(Base):
    __tablename__ = "productos"
    producto_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    precio: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    estacion: Mapped[str] = mapped_column(String(30))
    agotado: Mapped[bool] = mapped_column(Boolean, default=False)


class RecetaRow(Base):
    __tablename__ = "recetas"
    producto_id: Mapped[str] = mapped_column(ForeignKey("productos.producto_id"), primary_key=True)
    ingrediente_id: Mapped[str] = mapped_column(
        ForeignKey("ingredientes.ingrediente_id"), primary_key=True
    )
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 3))


class PromocionRow(Base):
    __tablename__ = "promociones"
    promocion_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    hora_inicio: Mapped[str] = mapped_column(String(8))
    hora_fin: Mapped[str] = mapped_column(String(8))
    condiciones: Mapped[list] = mapped_column(JSON)
    descuento_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    vigente: Mapped[bool] = mapped_column(Boolean, default=True)


class PedidoRow(Base):
    __tablename__ = "pedidos"
    pedido_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    canal: Mapped[str] = mapped_column(String(20))
    cliente_id: Mapped[str] = mapped_column(ForeignKey("clientes.cliente_id"), index=True)
    estado: Mapped[str] = mapped_column(String(20), index=True)
    autorizado: Mapped[bool] = mapped_column(Boolean, default=False)
    promocion_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    descuento: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    beneficio_aplicado: Mapped[bool] = mapped_column(Boolean, default=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime)
    cancel_motivo: Mapped[str | None] = mapped_column(String(300), nullable=True)
    cancel_usuario: Mapped[str | None] = mapped_column(String(60), nullable=True)
    cancel_fecha: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=0)


class LineaRow(Base):
    __tablename__ = "lineas_pedido"
    pedido_id: Mapped[str] = mapped_column(ForeignKey("pedidos.pedido_id"), primary_key=True)
    linea_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    producto_id: Mapped[str] = mapped_column(ForeignKey("productos.producto_id"))
    cantidad: Mapped[int] = mapped_column(Integer)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    estacion: Mapped[str] = mapped_column(String(30))
    estado_preparacion: Mapped[str] = mapped_column(String(20))
    modificaciones: Mapped[list] = mapped_column(JSON, default=list)


class HistorialRow(Base):
    __tablename__ = "historial_pedido"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pedido_id: Mapped[str] = mapped_column(ForeignKey("pedidos.pedido_id"), index=True)
    accion: Mapped[str] = mapped_column(String(120))
    usuario: Mapped[str] = mapped_column(String(60))
    fecha: Mapped[datetime] = mapped_column(DateTime)
    detalle: Mapped[str] = mapped_column(String(300), default="")


class EventoRow(Base):
    """Bitácora de eventos de dominio, escrita en la misma transacción que el cambio."""

    __tablename__ = "eventos_dominio"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(80), index=True)
    agregado_id: Mapped[str] = mapped_column(String(40), index=True)
    usuario: Mapped[str] = mapped_column(String(60), default="")
    ocurrido_en: Mapped[datetime] = mapped_column(DateTime)
    detalle: Mapped[dict] = mapped_column(JSON, default=dict)


class VentaRow(Base):
    """Modelo de lectura (CQRS): se genera con el evento PedidoCerrado (ADR-04)."""

    __tablename__ = "ventas_resumen"
    pedido_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    canal: Mapped[str] = mapped_column(String(20))
    fecha_cierre: Mapped[datetime] = mapped_column(DateTime, index=True)
    total_productos: Mapped[int] = mapped_column(Integer)
    total_importe: Mapped[Decimal] = mapped_column(Numeric(14, 2))
