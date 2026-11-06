"""Implementaciones SQL de los repositorios del dominio (informe U3, Tabla 33).

Mapean cada Aggregate a sus tablas y usan control de concurrencia optimista con una columna
`version` (ante un conflicto se lanza ConflictoDeConcurrencia).
"""

from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from src.application import ports
from src.domain.entities import Cliente, Ingrediente, LineaPedido, Pedido, Producto, Promocion
from src.domain.errors import ConflictoDeConcurrencia
from src.domain.specifications import CanalEn, TotalMinimo
from src.domain.value_objects import (
    Cancelacion,
    EstacionCocina,
    EstadoPreparacion,
    Modificacion,
    RegistroDeCambio,
    RequerimientoIngrediente,
    TipoModificacion,
    UmbralCritico,
    VentanaHoraria,
)
from src.infrastructure.modelos import (
    ClienteRow,
    HistorialRow,
    IngredienteRow,
    LineaRow,
    MovimientoRow,
    PedidoRow,
    ProductoRow,
    PromocionRow,
    RecetaRow,
)


class ClienteRepositorioSql(ports.IClienteRepository):
    def __init__(self, sesion: Session):
        self.s = sesion

    def obtener_por_id(self, cliente_id):
        fila = self.s.get(ClienteRow, cliente_id)
        if fila is None:
            return None
        return Cliente(fila.cliente_id, fila.nombre, fila.activo, fila.es_preferente, fila.ciudad)

    def guardar(self, cliente: Cliente):
        self.s.merge(
            ClienteRow(
                cliente_id=cliente.cliente_id,
                nombre=cliente.nombre,
                activo=cliente.activo,
                es_preferente=cliente.es_preferente,
                ciudad=cliente.ciudad,
            )
        )


class PedidoRepositorioSql(ports.IPedidoRepository):
    def __init__(self, sesion: Session):
        self.s = sesion

    # --- lectura ---
    def obtener_por_id(self, pedido_id):
        fila = self.s.get(PedidoRow, pedido_id)
        if fila is None:
            return None
        cancelacion = None
        if fila.cancel_motivo is not None:
            cancelacion = Cancelacion(fila.cancel_motivo, fila.cancel_usuario, fila.cancel_fecha)
        pedido = Pedido(
            fila.pedido_id,
            fila.canal,
            fila.cliente_id,
            fila.creado_en,
            estado=fila.estado,
            autorizado=fila.autorizado,
            promocion_id=fila.promocion_id,
            descuento=fila.descuento,
            beneficio_aplicado=fila.beneficio_aplicado,
            cancelacion=cancelacion,
            version=fila.version,
        )
        lineas = self.s.scalars(
            select(LineaRow).where(LineaRow.pedido_id == pedido_id).order_by(LineaRow.linea_id)
        )
        for lr in lineas:
            pedido.lineas.append(
                LineaPedido(
                    lr.linea_id,
                    lr.producto_id,
                    lr.cantidad,
                    Decimal(lr.precio_unitario),
                    EstacionCocina(lr.estacion),
                    EstadoPreparacion(lr.estado_preparacion),
                    [Modificacion(TipoModificacion(m["tipo"]), m["descripcion"]) for m in lr.modificaciones or []],
                )
            )
        historial = self.s.scalars(
            select(HistorialRow).where(HistorialRow.pedido_id == pedido_id).order_by(HistorialRow.id)
        )
        pedido.historial = [
            RegistroDeCambio(h.accion, h.usuario, h.fecha, h.detalle) for h in historial
        ]
        return pedido

    # --- escritura ---
    def agregar(self, pedido: Pedido):
        self.s.add(self._a_fila(pedido))
        self.s.flush()
        self._reemplazar_lineas(pedido)
        self._agregar_historial_nuevo(pedido)

    def guardar(self, pedido: Pedido):
        valores = self._valores(pedido)
        resultado = self.s.execute(
            update(PedidoRow)
            .where(PedidoRow.pedido_id == pedido.pedido_id, PedidoRow.version == pedido.version)
            .values(version=pedido.version + 1, **valores)
        )
        if resultado.rowcount != 1:
            raise ConflictoDeConcurrencia()
        pedido.version += 1
        self._reemplazar_lineas(pedido)
        self._agregar_historial_nuevo(pedido)

    # --- internos ---
    @staticmethod
    def _valores(p: Pedido) -> dict:
        c = p.cancelacion
        return {
            "canal": p.canal.value,
            "estado": p.estado.value,
            "autorizado": p.autorizado,
            "promocion_id": p.promocion_id,
            "descuento": p.descuento,
            "beneficio_aplicado": p.beneficio_aplicado,
            "cancel_motivo": c.motivo if c else None,
            "cancel_usuario": c.usuario if c else None,
            "cancel_fecha": c.fecha if c else None,
        }

    def _a_fila(self, p: Pedido) -> PedidoRow:
        return PedidoRow(
            pedido_id=p.pedido_id,
            cliente_id=p.cliente_id,
            creado_en=p.creado_en,
            version=p.version,
            **self._valores(p),
        )

    def _reemplazar_lineas(self, p: Pedido):
        self.s.execute(delete(LineaRow).where(LineaRow.pedido_id == p.pedido_id))
        for linea in p.lineas:
            self.s.add(
                LineaRow(
                    pedido_id=p.pedido_id,
                    linea_id=linea.linea_id,
                    producto_id=linea.producto_id,
                    cantidad=linea.cantidad,
                    precio_unitario=linea.precio_unitario,
                    estacion=linea.estacion.value,
                    estado_preparacion=linea.estado_preparacion.value,
                    modificaciones=[
                        {"tipo": m.tipo.value, "descripcion": m.descripcion}
                        for m in linea.modificaciones
                    ],
                )
            )

    def _agregar_historial_nuevo(self, p: Pedido):
        ya = self.s.scalar(
            select(func.count()).select_from(HistorialRow).where(HistorialRow.pedido_id == p.pedido_id)
        )
        for registro in p.historial[ya:]:  # el historial solo se agrega (RN-09)
            self.s.add(
                HistorialRow(
                    pedido_id=p.pedido_id,
                    accion=registro.accion,
                    usuario=registro.usuario,
                    fecha=registro.fecha,
                    detalle=registro.detalle,
                )
            )


class ProductoRepositorioSql(ports.IProductoRepository):
    def __init__(self, sesion: Session):
        self.s = sesion

    def _a_dominio(self, fila: ProductoRow, receta_filas) -> Producto:
        receta = [RequerimientoIngrediente(r.ingrediente_id, Decimal(r.cantidad)) for r in receta_filas]
        return Producto(
            fila.producto_id, fila.nombre, Decimal(fila.precio), fila.estacion, receta, fila.agotado
        )

    def obtener_por_id(self, producto_id):
        return self.obtener_por_ids([producto_id]).get(producto_id)

    def obtener_por_ids(self, producto_ids):
        ids = list(dict.fromkeys(producto_ids))
        if not ids:
            return {}
        filas = self.s.scalars(select(ProductoRow).where(ProductoRow.producto_id.in_(ids))).all()
        recetas: dict = {}
        for r in self.s.scalars(select(RecetaRow).where(RecetaRow.producto_id.in_(ids))):
            recetas.setdefault(r.producto_id, []).append(r)
        return {f.producto_id: self._a_dominio(f, recetas.get(f.producto_id, [])) for f in filas}

    def guardar(self, producto: Producto):
        self.s.merge(
            ProductoRow(
                producto_id=producto.producto_id,
                nombre=producto.nombre,
                precio=producto.precio,
                estacion=producto.estacion.value,
                agotado=producto.agotado,
            )
        )
        self.s.flush()
        self.s.execute(delete(RecetaRow).where(RecetaRow.producto_id == producto.producto_id))
        for req in producto.receta:
            self.s.add(
                RecetaRow(
                    producto_id=producto.producto_id,
                    ingrediente_id=req.ingrediente_id,
                    cantidad=req.cantidad,
                )
            )


class IngredienteRepositorioSql(ports.IIngredienteRepository):
    def __init__(self, sesion: Session):
        self.s = sesion

    @staticmethod
    def _a_dominio(f: IngredienteRow) -> Ingrediente:
        return Ingrediente(
            f.ingrediente_id,
            f.nombre,
            Decimal(f.existencia),
            UmbralCritico(Decimal(f.umbral)),
            f.unidad,
            f.version,
        )

    def obtener_por_id(self, ingrediente_id):
        fila = self.s.get(IngredienteRow, ingrediente_id)
        return self._a_dominio(fila) if fila else None

    def obtener_por_ids(self, ingrediente_ids):
        ids = list(dict.fromkeys(ingrediente_ids))
        if not ids:
            return {}
        filas = self.s.scalars(select(IngredienteRow).where(IngredienteRow.ingrediente_id.in_(ids)))
        return {f.ingrediente_id: self._a_dominio(f) for f in filas}

    def guardar(self, ingrediente: Ingrediente):
        existe = self.s.get(IngredienteRow, ingrediente.ingrediente_id)
        if existe is None:
            self.s.add(
                IngredienteRow(
                    ingrediente_id=ingrediente.ingrediente_id,
                    nombre=ingrediente.nombre,
                    unidad=ingrediente.unidad,
                    existencia=ingrediente.existencia,
                    umbral=ingrediente.umbral.cantidad,
                    version=ingrediente.version,
                )
            )
        else:
            self.s.expire(existe)
            resultado = self.s.execute(
                update(IngredienteRow)
                .where(
                    IngredienteRow.ingrediente_id == ingrediente.ingrediente_id,
                    IngredienteRow.version == ingrediente.version,
                )
                .values(
                    existencia=ingrediente.existencia,
                    umbral=ingrediente.umbral.cantidad,
                    version=ingrediente.version + 1,
                )
            )
            if resultado.rowcount != 1:
                raise ConflictoDeConcurrencia()
            ingrediente.version += 1
        for mov in ingrediente.movimientos_nuevos:  # los movimientos solo se agregan (RN-10)
            self.s.add(
                MovimientoRow(
                    ingrediente_id=ingrediente.ingrediente_id,
                    tipo=mov.tipo.value,
                    delta=mov.delta,
                    existencia_resultante=mov.existencia_resultante,
                    usuario=mov.usuario,
                    fecha=mov.fecha,
                    referencia=mov.referencia,
                )
            )
        ingrediente.movimientos_nuevos = []


def _condicion_a_dominio(cfg: dict):
    if cfg["tipo"] == "total_minimo":
        return TotalMinimo(Decimal(cfg["monto"]))
    if cfg["tipo"] == "canal":
        return CanalEn(*cfg["canales"])
    raise ValueError(f"condición desconocida: {cfg['tipo']}")


def _condicion_a_config(cond) -> dict:
    if isinstance(cond, TotalMinimo):
        return {"tipo": "total_minimo", "monto": str(cond.monto)}
    if isinstance(cond, CanalEn):
        return {"tipo": "canal", "canales": sorted(c.value for c in cond.canales)}
    raise ValueError("condición de promoción no soportada")


class PromocionRepositorioSql(ports.IPromocionRepository):
    def __init__(self, sesion: Session):
        self.s = sesion

    @staticmethod
    def _a_dominio(f: PromocionRow) -> Promocion:
        return Promocion(
            f.promocion_id,
            f.nombre,
            VentanaHoraria(time.fromisoformat(f.hora_inicio), time.fromisoformat(f.hora_fin)),
            [_condicion_a_dominio(c) for c in f.condiciones],
            Decimal(f.descuento_pct),
            f.vigente,
        )

    def obtener_por_id(self, promocion_id):
        fila = self.s.get(PromocionRow, promocion_id)
        return self._a_dominio(fila) if fila else None

    def obtener_vigentes(self, momento: datetime):
        filas = self.s.scalars(select(PromocionRow).where(PromocionRow.vigente.is_(True)))
        return [self._a_dominio(f) for f in filas]

    def guardar(self, promocion: Promocion):
        self.s.merge(
            PromocionRow(
                promocion_id=promocion.promocion_id,
                nombre=promocion.nombre,
                hora_inicio=promocion.ventana.inicio.strftime("%H:%M:%S"),
                hora_fin=promocion.ventana.fin.strftime("%H:%M:%S"),
                condiciones=[_condicion_a_config(c) for c in promocion.condiciones],
                descuento_pct=promocion.descuento_pct,
                vigente=promocion.vigente,
            )
        )
