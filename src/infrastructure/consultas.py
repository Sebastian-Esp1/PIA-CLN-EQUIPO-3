"""Implementación SQL del lado de lectura: consultas de solo lectura que devuelven DTO."""

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select

from src.application import ports
from src.application.dtos import (
    ComparativoInventarioDto,
    DisponibilidadProductoDto,
    HistorialPedidoItemDto,
    IngredienteCriticoDto,
    IngredienteDto,
    LineaDto,
    OrdenEstacionDto,
    PedidoDto,
    VentaResumenDto,
)
from src.domain.services import DisponibilidadProductos
from src.infrastructure.modelos import (
    HistorialRow,
    IngredienteRow,
    LineaRow,
    MovimientoRow,
    PedidoRow,
    ProductoRow,
    RecetaRow,
    VentaRow,
)
from src.infrastructure.repositorios import IngredienteRepositorioSql, ProductoRepositorioSql

CERO = Decimal("0")


class ConsultasDePedidosSql(ports.IConsultasDePedidos):
    def __init__(self, fabrica):
        self._fabrica = fabrica

    def _a_dto(self, sesion, fila: PedidoRow) -> PedidoDto:
        lineas = sesion.scalars(
            select(LineaRow).where(LineaRow.pedido_id == fila.pedido_id).order_by(LineaRow.linea_id)
        ).all()
        dtos = [
            LineaDto(
                lr.linea_id,
                lr.producto_id,
                lr.cantidad,
                Decimal(lr.precio_unitario),
                Decimal(lr.precio_unitario) * lr.cantidad,
                lr.estacion,
                lr.estado_preparacion,
                lr.modificaciones or [],
            )
            for lr in lineas
        ]
        total = sum((d.subtotal for d in dtos), CERO)
        descuento = Decimal(fila.descuento)
        return PedidoDto(
            fila.pedido_id,
            fila.canal,
            fila.cliente_id,
            fila.estado,
            fila.autorizado,
            fila.promocion_id,
            fila.beneficio_aplicado,
            total,
            descuento,
            total - descuento,
            dtos,
            (
                {
                    "motivo": fila.cancel_motivo,
                    "usuario": fila.cancel_usuario,
                    "fecha": fila.cancel_fecha,
                }
                if fila.cancel_motivo is not None
                else None
            ),
        )

    def obtener(self, pedido_id):
        with self._fabrica() as sesion:
            fila = sesion.get(PedidoRow, pedido_id)
            return self._a_dto(sesion, fila) if fila else None

    def listar(self, estado, limite):
        with self._fabrica() as sesion:
            consulta = select(PedidoRow).order_by(PedidoRow.pedido_id).limit(limite)
            if estado:
                consulta = consulta.where(PedidoRow.estado == estado)
            return [self._a_dto(sesion, f) for f in sesion.scalars(consulta)]

    def historial(self, pedido_id):
        with self._fabrica() as sesion:
            filas = sesion.scalars(
                select(HistorialRow)
                .where(HistorialRow.pedido_id == pedido_id)
                .order_by(HistorialRow.fecha, HistorialRow.id)
            )
            return [HistorialPedidoItemDto(h.accion, h.usuario, h.fecha, h.detalle) for h in filas]

    def ordenes_de_estacion(self, estacion):
        """US-07: cada estación ve únicamente sus productos pendientes o en preparación."""
        with self._fabrica() as sesion:
            filas = sesion.execute(
                select(LineaRow, PedidoRow, ProductoRow)
                .join(PedidoRow, PedidoRow.pedido_id == LineaRow.pedido_id)
                .join(ProductoRow, ProductoRow.producto_id == LineaRow.producto_id)
                .where(
                    LineaRow.estacion == estacion.value,
                    PedidoRow.estado.in_(["CONFIRMADO", "EN_PREPARACION"]),
                    LineaRow.estado_preparacion != "LISTA",
                )
                .order_by(PedidoRow.creado_en, PedidoRow.pedido_id, LineaRow.linea_id)
            ).all()
            return [
                OrdenEstacionDto(
                    p.pedido_id,
                    p.canal,
                    lr.linea_id,
                    prod.nombre,
                    lr.cantidad,
                    lr.modificaciones or [],
                    lr.estado_preparacion,
                )
                for lr, p, prod in filas
            ]


class ConsultasDeInventarioSql(ports.IConsultasDeInventario):
    def __init__(self, fabrica):
        self._fabrica = fabrica

    def disponibilidad_de_productos(self):
        """US-04: usa el mismo Domain Service que el alta de líneas, para no duplicar la regla."""
        with self._fabrica() as sesion:
            productos = ProductoRepositorioSql(sesion).obtener_por_ids(
                sesion.scalars(select(ProductoRow.producto_id)).all()
            )
            ids = {r.ingrediente_id for p in productos.values() for r in p.receta}
            ingredientes = IngredienteRepositorioSql(sesion).obtener_por_ids(list(ids))
            servicio = DisponibilidadProductos()
            resultado = []
            for producto in sorted(productos.values(), key=lambda p: p.producto_id):
                disp = servicio.evaluar(producto, 1, ingredientes)
                resultado.append(
                    DisponibilidadProductoDto(
                        producto.producto_id, producto.nombre, disp.disponible, disp.motivo
                    )
                )
            return resultado

    def ingredientes(self):
        with self._fabrica() as sesion:
            filas = sesion.scalars(select(IngredienteRow).order_by(IngredienteRow.ingrediente_id))
            return [
                IngredienteDto(
                    f.ingrediente_id,
                    f.nombre,
                    Decimal(f.existencia),
                    Decimal(f.umbral),
                    Decimal(f.existencia) <= Decimal(f.umbral),
                )
                for f in filas
            ]

    def ingredientes_criticos(self):
        """US-10: ingredientes con existencia <= umbral y los productos que se ven afectados."""
        with self._fabrica() as sesion:
            criticos = [
                f
                for f in sesion.scalars(select(IngredienteRow).order_by(IngredienteRow.ingrediente_id))
                if Decimal(f.existencia) <= Decimal(f.umbral)
            ]
            resultado = []
            for f in criticos:
                afectados = sesion.scalars(
                    select(ProductoRow.nombre)
                    .join(RecetaRow, RecetaRow.producto_id == ProductoRow.producto_id)
                    .where(RecetaRow.ingrediente_id == f.ingrediente_id)
                    .order_by(ProductoRow.producto_id)
                ).all()
                resultado.append(
                    IngredienteCriticoDto(
                        f.ingrediente_id,
                        f.nombre,
                        Decimal(f.existencia),
                        Decimal(f.umbral),
                        list(afectados),
                    )
                )
            return resultado

    def comparativo(self, desde, hasta):
        """US-14 / RN-15: esperado (entradas y salidas teóricas) contra registrado (con conteos)."""
        with self._fabrica() as sesion:
            movimientos = sesion.scalars(
                select(MovimientoRow)
                .where(MovimientoRow.fecha >= desde, MovimientoRow.fecha <= hasta)
                .order_by(MovimientoRow.id)
            ).all()
            nombres = {
                i.ingrediente_id: i.nombre for i in sesion.scalars(select(IngredienteRow))
            }
        por_ingrediente = defaultdict(list)
        for mov in movimientos:
            por_ingrediente[mov.ingrediente_id].append(mov)
        resultado = []
        for ingrediente_id, movs in sorted(por_ingrediente.items()):
            primero = movs[0]
            inicial = Decimal(primero.existencia_resultante) - Decimal(primero.delta)
            teorico = sum((Decimal(m.delta) for m in movs if m.tipo != "CONTEO"), CERO)
            esperada = inicial + teorico
            registrada = Decimal(movs[-1].existencia_resultante)
            resultado.append(
                ComparativoInventarioDto(
                    ingrediente_id,
                    nombres.get(ingrediente_id, ingrediente_id),
                    esperada,
                    registrada,
                    registrada - esperada,
                )
            )
        return resultado


class ConsultasDeVentasSql(ports.IConsultasDeVentas):
    def __init__(self, fabrica):
        self._fabrica = fabrica

    def ventas_por_periodo(self, desde, hasta):
        with self._fabrica() as sesion:
            filas = sesion.scalars(
                select(VentaRow)
                .where(VentaRow.fecha_cierre >= desde, VentaRow.fecha_cierre <= hasta)
                .order_by(VentaRow.fecha_cierre)
            )
            return [
                VentaResumenDto(
                    v.pedido_id, v.canal, v.fecha_cierre, v.total_productos, Decimal(v.total_importe)
                )
                for v in filas
            ]
