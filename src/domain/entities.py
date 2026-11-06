"""Aggregates del dominio: Pedido, Producto, Ingrediente, Promoción y la referencia Cliente."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from src.domain import events as ev
from src.domain.errors import (
    CancelacionNoPermitida,
    DatoInvalido,
    ExistenciaInsuficiente,
    MotivoDeCancelacionRequerido,
    PedidoNoModificable,
    PedidoNoProcesable,
)
from src.domain.specifications import (
    EvaluacionPedido,
    Specification,
    califica_beneficio,
    puede_procesarse,
)
from src.domain.state_machine import MAQUINA_PEDIDO, EstadoPedido
from src.domain.value_objects import (
    CanalVenta,
    Cancelacion,
    Disponibilidad,
    EstacionCocina,
    EstadoPreparacion,
    Modificacion,
    MovimientoInventario,
    RegistroDeCambio,
    RequerimientoIngrediente,
    TipoModificacion,
    TipoMovimiento,
    UmbralCritico,
    VentanaHoraria,
    a_decimal,
)

CERO = Decimal("0")


# --- Cliente (comensal) ---------------------------------------------------------------------
@dataclass
class Cliente:
    """Actor que hace el pedido. Los atributos vienen del paquete de datos del docente."""

    cliente_id: str
    nombre: str
    activo: bool = True
    es_preferente: bool = False
    ciudad: str = ""


# --- Aggregate Pedido -----------------------------------------------------------------------
@dataclass
class LineaPedido:
    linea_id: int
    producto_id: str
    cantidad: int
    precio_unitario: Decimal
    estacion: EstacionCocina
    estado_preparacion: EstadoPreparacion = EstadoPreparacion.PENDIENTE
    modificaciones: list = field(default_factory=list)

    def __post_init__(self):
        if isinstance(self.cantidad, bool) or not isinstance(self.cantidad, int):
            raise DatoInvalido("La cantidad debe ser un número entero")
        if self.cantidad <= 0:
            raise DatoInvalido("La cantidad debe ser mayor a cero")
        self.precio_unitario = a_decimal(self.precio_unitario, "precio")
        if self.precio_unitario < 0:
            raise DatoInvalido("El precio no puede ser negativo")

    @property
    def subtotal(self) -> Decimal:
        return self.precio_unitario * self.cantidad


class ResultadoLinea:
    """Resultado de agregar una línea: Agregado o Rechazado(motivo) (informe U3, Tabla 27)."""

    def __init__(self, agregada: bool, linea=None, motivo: str = ""):
        self.agregada, self.linea, self.motivo = agregada, linea, motivo


class Pedido:
    def __init__(
        self,
        pedido_id: str,
        canal: CanalVenta,
        cliente_id: str,
        creado_en: datetime,
        estado: EstadoPedido = EstadoPedido.EN_REGISTRO,
        autorizado: bool = False,
        promocion_id: str | None = None,
        descuento: Decimal = CERO,
        beneficio_aplicado: bool = False,
        cancelacion: Cancelacion | None = None,
        version: int = 0,
    ):
        self.pedido_id = pedido_id
        self.canal = CanalVenta(canal)
        self.cliente_id = cliente_id
        self.creado_en = creado_en
        self.estado = EstadoPedido(estado)
        self.autorizado = autorizado
        self.promocion_id = promocion_id
        self.descuento = a_decimal(descuento, "descuento")
        self.beneficio_aplicado = beneficio_aplicado
        self.cancelacion = cancelacion
        self.version = version
        self.lineas: list[LineaPedido] = []
        self.historial: list[RegistroDeCambio] = []
        self._eventos: list = []

    # --- fábrica y rehidratación ---------------------------------------------------------
    @classmethod
    def iniciar(cls, pedido_id, canal, cliente_id, usuario, ahora):
        """RN-01 (canal obligatorio): nace en EN_REGISTRO con su primer registro de cambio."""
        try:
            canal = CanalVenta(canal)
        except ValueError as exc:
            raise DatoInvalido("El canal debe ser MESA, TELEFONO, WHATSAPP o DOMICILIO") from exc
        if not cliente_id:
            raise DatoInvalido("El pedido necesita un cliente")
        pedido = cls(pedido_id, canal, cliente_id, ahora)
        pedido._registrar("Pedido iniciado", usuario, ahora, f"canal={canal.value}")
        pedido._emitir(ev.PedidoIniciado, ahora, usuario, canal=canal.value, cliente=cliente_id)
        return pedido

    # --- consultas -----------------------------------------------------------------------
    @property
    def total(self) -> Decimal:
        return sum((linea.subtotal for linea in self.lineas), CERO)

    @property
    def total_a_pagar(self) -> Decimal:
        return self.total - self.descuento

    @property
    def promocion_activa(self) -> bool:
        return self.promocion_id is not None

    def linea(self, linea_id: int) -> LineaPedido:
        for linea in self.lineas:
            if linea.linea_id == linea_id:
                return linea
        raise DatoInvalido(f"La línea {linea_id} no existe en el pedido")

    def extraer_eventos(self) -> list:
        eventos, self._eventos = self._eventos, []
        return eventos

    # --- comportamiento ------------------------------------------------------------------
    def agregar_linea(
        self, producto, cantidad, disponibilidad: Disponibilidad, usuario, ahora
    ) -> ResultadoLinea:
        """INV-P1, INV-P2, INV-P3: solo en EN_REGISTRO y si el producto está disponible."""
        self._exigir_modificable()
        if self.estado is not EstadoPedido.EN_REGISTRO:
            raise PedidoNoModificable("Solo se agregan productos mientras el pedido está en registro.")
        if not disponibilidad.disponible:
            self._registrar(
                "Producto rechazado por disponibilidad",
                usuario,
                ahora,
                f"{producto.producto_id}: {disponibilidad.motivo}",
            )
            self._emitir(
                ev.ProductoRechazadoPorDisponibilidad,
                ahora,
                usuario,
                producto=producto.producto_id,
                motivo=disponibilidad.motivo,
            )
            return ResultadoLinea(False, motivo=disponibilidad.motivo)
        linea = LineaPedido(
            linea_id=len(self.lineas) + 1,
            producto_id=producto.producto_id,
            cantidad=cantidad,
            precio_unitario=producto.precio,
            estacion=producto.estacion,
        )
        self.lineas.append(linea)
        self._registrar(
            "Línea agregada", usuario, ahora, f"{producto.producto_id} x{linea.cantidad}"
        )
        return ResultadoLinea(True, linea)

    def agregar_modificacion(self, linea_id, tipo, descripcion, usuario, ahora):
        """RN-03: la modificación o extra queda asociada a una línea existente."""
        self._exigir_modificable()
        linea = self.linea(linea_id)
        try:
            tipo = TipoModificacion(tipo)
        except ValueError as exc:
            raise DatoInvalido("El tipo debe ser QUITAR, CAMBIAR o AGREGAR") from exc
        linea.modificaciones.append(Modificacion(tipo, descripcion))
        self._registrar("Modificación agregada", usuario, ahora, f"línea {linea_id}: {descripcion}")
        self._emitir(
            ev.ModificacionAgregada, ahora, usuario, linea=linea_id, tipo=tipo.value
        )

    def autorizar(self, usuario, ahora):
        """Precondición `autorizacion` del paquete del docente (R1)."""
        if self.estado is not EstadoPedido.EN_REGISTRO:
            raise PedidoNoModificable("Solo se autoriza un pedido que está en registro.")
        self.autorizado = True
        self._registrar("Pedido autorizado", usuario, ahora)
        self._emitir(ev.PedidoAutorizado, ahora, usuario)

    def confirmar(self, usuario, cliente: Cliente, ahora, promocion=None):
        """Envía el pedido a cocina (RN-04). Exige R1 y una transición válida (INV-P4)."""
        MAQUINA_PEDIDO.validar(self.estado, EstadoPedido.CONFIRMADO)
        evaluacion = EvaluacionPedido(self, cliente, ahora)
        regla = puede_procesarse()
        if not regla.es_satisfecha_por(evaluacion):
            motivos = "; ".join(regla.motivos_de_fallo(evaluacion))
            raise PedidoNoProcesable(f"El pedido no puede procesarse: {motivos}.")
        if promocion is not None and not self.promocion_activa:
            self.promocion_id = promocion.promocion_id
            self.descuento = promocion.calcular_descuento(self.total)
            self._emitir(
                ev.PromocionAplicada,
                ahora,
                usuario,
                promocion=promocion.promocion_id,
                descuento=str(self.descuento),
            )
        if califica_beneficio().es_satisfecha_por(evaluacion):
            self.beneficio_aplicado = True
            self._emitir(ev.BeneficioPreferenteAplicado, ahora, usuario, total=str(self.total))
        self.estado = EstadoPedido.CONFIRMADO
        self._registrar("Pedido confirmado", usuario, ahora, "enviado a cocina e inventario")
        self._emitir(
            ev.PedidoConfirmado, ahora, usuario, total=str(self.total), lineas=len(self.lineas)
        )

    def iniciar_preparacion_de_linea(self, linea_id, usuario, ahora):
        """RN-05: cada estación prepara solo sus productos."""
        if self.estado not in (EstadoPedido.CONFIRMADO, EstadoPedido.EN_PREPARACION):
            raise PedidoNoModificable("El pedido debe estar confirmado para prepararse.")
        linea = self.linea(linea_id)
        if linea.estado_preparacion is not EstadoPreparacion.PENDIENTE:
            raise DatoInvalido("La línea ya fue iniciada")
        if self.estado is EstadoPedido.CONFIRMADO:
            MAQUINA_PEDIDO.validar(self.estado, EstadoPedido.EN_PREPARACION)
            self.estado = EstadoPedido.EN_PREPARACION
        linea.estado_preparacion = EstadoPreparacion.EN_PREPARACION
        self._registrar("Preparación iniciada", usuario, ahora, f"línea {linea_id}")

    def marcar_linea_lista(self, linea_id, usuario, ahora) -> bool:
        """RN-06 / INV-P5: el pedido pasa a LISTO solo cuando todas sus líneas están listas."""
        if self.estado is not EstadoPedido.EN_PREPARACION:
            raise PedidoNoModificable("El pedido no está en preparación.")
        linea = self.linea(linea_id)
        if linea.estado_preparacion is not EstadoPreparacion.EN_PREPARACION:
            raise DatoInvalido("La línea debe estar en preparación para marcarse lista")
        linea.estado_preparacion = EstadoPreparacion.LISTA
        self._registrar("Línea lista", usuario, ahora, f"línea {linea_id}")
        self._emitir(ev.LineaPreparada, ahora, usuario, linea=linea_id)
        if all(item.estado_preparacion is EstadoPreparacion.LISTA for item in self.lineas):
            MAQUINA_PEDIDO.validar(self.estado, EstadoPedido.LISTO)
            self.estado = EstadoPedido.LISTO
            self._registrar("Pedido listo", usuario, ahora)
            self._emitir(ev.PedidoListo, ahora, usuario)
            return True
        return False

    def cerrar(self, usuario, ahora):
        """RN-14: una venta se registra a partir de un pedido procesado y cerrado."""
        MAQUINA_PEDIDO.validar(self.estado, EstadoPedido.CERRADO)
        self.estado = EstadoPedido.CERRADO
        self._registrar("Pedido cerrado", usuario, ahora, "entregado")
        self._emitir(
            ev.PedidoCerrado,
            ahora,
            usuario,
            total=str(self.total_a_pagar),
            unidades=sum(item.cantidad for item in self.lineas),
            canal=self.canal.value,
        )

    def cancelar(self, motivo, usuario, ahora):
        """RN-07, INV-P6. La autorización del usuario (SP-05) se verifica en la aplicación."""
        if not isinstance(motivo, str) or not motivo.strip():
            raise MotivoDeCancelacionRequerido()
        if not self.estado.permite_cancelar:
            raise CancelacionNoPermitida()
        estado_previo = self.estado
        MAQUINA_PEDIDO.validar(self.estado, EstadoPedido.CANCELADO)
        self.estado = EstadoPedido.CANCELADO
        self.cancelacion = Cancelacion(motivo.strip(), usuario, ahora)
        self._registrar("Pedido cancelado", usuario, ahora, f"motivo: {motivo.strip()}")
        self._emitir(
            ev.PedidoCancelado,
            ahora,
            usuario,
            motivo=motivo.strip(),
            estado_previo=estado_previo.value,
        )
        return estado_previo

    # --- internos ------------------------------------------------------------------------
    def _exigir_modificable(self):
        if not self.estado.permite_modificar:
            raise PedidoNoModificable("El pedido ya está en preparación y no admite cambios.")

    def _registrar(self, accion, usuario, ahora, detalle=""):
        self.historial.append(RegistroDeCambio(accion, usuario, ahora, detalle))

    def _emitir(self, clase_evento, ahora, usuario, **detalle):
        self._eventos.append(clase_evento(ahora, self.pedido_id, usuario, detalle))


# --- Aggregate Producto ---------------------------------------------------------------------
class Producto:
    def __init__(
        self,
        producto_id: str,
        nombre: str,
        precio: Decimal,
        estacion: EstacionCocina,
        receta: list[RequerimientoIngrediente],
        agotado: bool = False,
    ):
        if not receta:
            raise DatoInvalido("La receta necesita al menos un ingrediente")  # INV-R1
        self.producto_id = producto_id
        self.nombre = nombre
        self.precio = a_decimal(precio, "precio")
        self.estacion = EstacionCocina(estacion)
        self.receta = list(receta)
        self.agotado = agotado
        self._eventos: list = []

    def marcar_agotado(self, usuario, ahora):
        self.agotado = True
        self._eventos.append(ev.ProductoMarcadoAgotado(ahora, self.producto_id, usuario))

    def reactivar(self, usuario, ahora):
        self.agotado = False
        self._eventos.append(ev.ProductoReactivado(ahora, self.producto_id, usuario))

    def cambiar_receta(self, receta):
        if not receta:
            raise DatoInvalido("La receta necesita al menos un ingrediente")
        self.receta = list(receta)

    def extraer_eventos(self):
        eventos, self._eventos = self._eventos, []
        return eventos


# --- Aggregate Ingrediente ------------------------------------------------------------------
class Ingrediente:
    def __init__(
        self,
        ingrediente_id: str,
        nombre: str,
        existencia: Decimal,
        umbral: UmbralCritico,
        unidad: str = "pza",
        version: int = 0,
    ):
        self.ingrediente_id = ingrediente_id
        self.nombre = nombre
        self.existencia = a_decimal(existencia, "existencia")
        if self.existencia < 0:
            raise DatoInvalido("La existencia no puede ser negativa")  # INV-I1
        self.umbral = umbral
        self.unidad = unidad
        self.version = version
        self.movimientos_nuevos: list[MovimientoInventario] = []
        self._eventos: list = []

    @property
    def es_critico(self) -> bool:
        """INV-I3: derivado, nunca almacenado (decisión D-10)."""
        return self.existencia <= self.umbral.cantidad

    def definir_umbral(self, umbral: UmbralCritico):
        self.umbral = umbral

    def registrar_entrada(self, cantidad, usuario, ahora, referencia=""):
        cantidad = self._cantidad_positiva(cantidad)
        self._aplicar(TipoMovimiento.ENTRADA, cantidad, usuario, ahora, referencia)

    def registrar_salida(self, cantidad, usuario, ahora, referencia=""):
        cantidad = self._cantidad_positiva(cantidad)
        if cantidad > self.existencia:
            raise ExistenciaInsuficiente(
                f"No hay existencia suficiente de {self.nombre}: hay {self.existencia} y "
                f"se piden {cantidad}."
            )
        self._aplicar(TipoMovimiento.SALIDA, -cantidad, usuario, ahora, referencia)

    def registrar_conteo(self, cantidad_contada, usuario, ahora, referencia=""):
        contada = a_decimal(cantidad_contada, "cantidad")
        if contada < 0:
            raise DatoInvalido("La cantidad contada no puede ser negativa")
        self._aplicar(TipoMovimiento.CONTEO, contada - self.existencia, usuario, ahora, referencia)

    def extraer_eventos(self):
        eventos, self._eventos = self._eventos, []
        return eventos

    def _cantidad_positiva(self, cantidad) -> Decimal:
        cantidad = a_decimal(cantidad, "cantidad")
        if cantidad <= 0:
            raise DatoInvalido("La cantidad debe ser mayor a cero")
        return cantidad

    def _aplicar(self, tipo, delta, usuario, ahora, referencia):
        era_critico = self.es_critico
        self.existencia = self.existencia + delta
        self.movimientos_nuevos.append(
            MovimientoInventario(tipo, delta, self.existencia, usuario, ahora, referencia)
        )
        self._eventos.append(
            ev.ExistenciaActualizada(
                ahora,
                self.ingrediente_id,
                usuario,
                {"tipo": tipo.value, "existencia": str(self.existencia)},
            )
        )
        if self.es_critico and not era_critico:  # solo al cruzar el umbral
            self._eventos.append(
                ev.IngredienteMarcadoCritico(
                    ahora,
                    self.ingrediente_id,
                    usuario,
                    {"existencia": str(self.existencia), "umbral": str(self.umbral.cantidad)},
                )
            )


# --- Aggregate Promoción --------------------------------------------------------------------
class Promocion:
    def __init__(
        self,
        promocion_id: str,
        nombre: str,
        ventana: VentanaHoraria,
        condiciones: list[Specification],
        descuento_pct: Decimal = CERO,
        vigente: bool = True,
    ):
        if not condiciones:
            raise DatoInvalido("La promoción necesita al menos una condición")  # INV-M2
        pct = a_decimal(descuento_pct, "descuento")
        if not CERO <= pct <= Decimal("100"):
            raise DatoInvalido("El descuento debe estar entre 0 y 100")
        self.promocion_id = promocion_id
        self.nombre = nombre
        self.ventana = ventana
        self.condiciones = list(condiciones)
        self.descuento_pct = pct
        self.vigente = vigente

    def activar(self):
        self.vigente = True

    def desactivar(self):
        self.vigente = False

    def evaluar(self, evaluacion: EvaluacionPedido) -> bool:
        """INV-M3: vigente, dentro de la ventana y con todas las condiciones. Sin efectos."""
        if not self.vigente or not self.ventana.contiene(evaluacion.momento):
            return False
        return all(cond.es_satisfecha_por(evaluacion) for cond in self.condiciones)

    def calcular_descuento(self, total: Decimal) -> Decimal:
        return (total * self.descuento_pct / Decimal(100)).quantize(Decimal("0.01"))
