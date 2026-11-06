"""Service Layer: cada método expresa una intención completa del usuario y coordina; las reglas
de negocio viven en el dominio (informe U3, sección 5). Una transacción por método de escritura.
"""

from decimal import Decimal

from src.application import commands as cmd
from src.application.dtos import (
    IngredienteDto,
    LineaDto,
    PedidoDto,
    ResultadoAgregarProducto,
    ResultadoMarcarLista,
)
from src.application.ports import Accion, IAutorizador, IReloj, Usuario
from src.domain.entities import Promocion
from src.domain.errors import (
    DatoInvalido,
    NoAutorizado,
    ProductoNoDisponible,
    RecursoNoEncontrado,
)
from src.domain.services import ConsumoDeIngredientes, DisponibilidadProductos, EvaluadorPromociones
from src.domain.specifications import CanalEn, EvaluacionPedido, TotalMinimo
from src.domain.state_machine import EstadoPedido
from src.domain.value_objects import UmbralCritico, VentanaHoraria


def a_dto(pedido) -> PedidoDto:
    return PedidoDto(
        pedido_id=pedido.pedido_id,
        canal=pedido.canal.value,
        cliente_id=pedido.cliente_id,
        estado=pedido.estado.value,
        autorizado=pedido.autorizado,
        promocion_id=pedido.promocion_id,
        beneficio_aplicado=pedido.beneficio_aplicado,
        total=pedido.total,
        descuento=pedido.descuento,
        total_a_pagar=pedido.total_a_pagar,
        lineas=[
            LineaDto(
                linea.linea_id,
                linea.producto_id,
                linea.cantidad,
                linea.precio_unitario,
                linea.subtotal,
                linea.estacion.value,
                linea.estado_preparacion.value,
                [{"tipo": m.tipo.value, "descripcion": m.descripcion} for m in linea.modificaciones],
            )
            for linea in pedido.lineas
        ],
        cancelacion=(
            {
                "motivo": pedido.cancelacion.motivo,
                "usuario": pedido.cancelacion.usuario,
                "fecha": pedido.cancelacion.fecha,
            }
            if pedido.cancelacion
            else None
        ),
    )


class _ServicioBase:
    def __init__(self, uow_factory, reloj: IReloj, autorizador: IAutorizador):
        self._uow_factory = uow_factory
        self._reloj = reloj
        self._autorizador = autorizador

    def _exigir(self, usuario: Usuario, accion: Accion):
        if not self._autorizador.puede(usuario, accion):
            raise NoAutorizado(f"El rol {usuario.rol.value} no puede realizar {accion.value}.")

    @staticmethod
    def _obtener_pedido(uow, pedido_id):
        pedido = uow.pedidos.obtener_por_id(pedido_id)
        if pedido is None:
            raise RecursoNoEncontrado(f"El pedido {pedido_id} no existe.")
        return pedido


class ServicioDePedidos(_ServicioBase):
    """CU-01 y CU-04. Cada método es el handler del Command del mismo nombre."""

    def __init__(self, uow_factory, reloj, autorizador, generador_de_ids):
        super().__init__(uow_factory, reloj, autorizador)
        self._ids = generador_de_ids
        self._disponibilidad = DisponibilidadProductos()
        self._consumo = ConsumoDeIngredientes()
        self._promociones = EvaluadorPromociones()

    def iniciar_pedido(self, c: cmd.IniciarPedido) -> PedidoDto:
        self._exigir(c.usuario, Accion.REGISTRAR_PEDIDOS)
        from src.domain.entities import Pedido

        with self._uow_factory() as uow:
            if uow.clientes.obtener_por_id(c.cliente_id) is None:
                raise RecursoNoEncontrado(f"El cliente {c.cliente_id} no existe.")
            pedido = Pedido.iniciar(
                self._ids(), c.canal, c.cliente_id, c.usuario.usuario_id, self._reloj.ahora()
            )
            uow.pedidos.agregar(pedido)
            uow.registrar_eventos(pedido.extraer_eventos())
            uow.confirmar()
            return a_dto(pedido)

    def agregar_producto_al_pedido(self, c: cmd.AgregarProductoAlPedido) -> ResultadoAgregarProducto:
        """CU-01 / CU-02: si no hay disponibilidad la línea no se agrega pero queda la incidencia."""
        self._exigir(c.usuario, Accion.REGISTRAR_PEDIDOS)
        if isinstance(c.cantidad, bool) or not isinstance(c.cantidad, int) or c.cantidad <= 0:
            raise DatoInvalido("La cantidad debe ser un entero mayor a cero")
        with self._uow_factory() as uow:
            pedido = self._obtener_pedido(uow, c.pedido_id)
            producto = uow.productos.obtener_por_id(c.producto_id)
            if producto is None:
                raise RecursoNoEncontrado(f"El producto {c.producto_id} no existe.")
            ingredientes = uow.ingredientes.obtener_por_ids(
                [req.ingrediente_id for req in producto.receta]
            )
            ya_pedido = sum(
                linea.cantidad for linea in pedido.lineas if linea.producto_id == c.producto_id
            )
            disponibilidad = self._disponibilidad.evaluar(
                producto, ya_pedido + c.cantidad, ingredientes
            )
            resultado = pedido.agregar_linea(
                producto, c.cantidad, disponibilidad, c.usuario.usuario_id, self._reloj.ahora()
            )
            uow.pedidos.guardar(pedido)
            uow.registrar_eventos(pedido.extraer_eventos())
            uow.confirmar()
            return ResultadoAgregarProducto(resultado.agregada, resultado.motivo, a_dto(pedido))

    def agregar_modificacion(self, c: cmd.AgregarModificacion) -> PedidoDto:
        self._exigir(c.usuario, Accion.REGISTRAR_PEDIDOS)
        with self._uow_factory() as uow:
            pedido = self._obtener_pedido(uow, c.pedido_id)
            pedido.agregar_modificacion(
                c.linea_id, c.tipo, c.descripcion, c.usuario.usuario_id, self._reloj.ahora()
            )
            uow.pedidos.guardar(pedido)
            uow.registrar_eventos(pedido.extraer_eventos())
            uow.confirmar()
            return a_dto(pedido)

    def autorizar_pedido(self, c: cmd.AutorizarPedido) -> PedidoDto:
        self._exigir(c.usuario, Accion.REGISTRAR_PEDIDOS)
        with self._uow_factory() as uow:
            pedido = self._obtener_pedido(uow, c.pedido_id)
            pedido.autorizar(c.usuario.usuario_id, self._reloj.ahora())
            uow.pedidos.guardar(pedido)
            uow.registrar_eventos(pedido.extraer_eventos())
            uow.confirmar()
            return a_dto(pedido)

    def confirmar_pedido(self, c: cmd.ConfirmarPedido) -> PedidoDto:
        """CU-01 (ADR-03): confirma el pedido y descuenta ingredientes en una sola transacción.

        Si algo falla (regla R1, disponibilidad o existencia) la transacción se revierte completa.
        """
        self._exigir(c.usuario, Accion.REGISTRAR_PEDIDOS)
        ahora = self._reloj.ahora()
        with self._uow_factory() as uow:
            pedido = self._obtener_pedido(uow, c.pedido_id)
            cliente = uow.clientes.obtener_por_id(pedido.cliente_id)
            if cliente is None:
                raise RecursoNoEncontrado(f"El cliente {pedido.cliente_id} no existe.")
            promocion = self._promociones.aplicable(
                EvaluacionPedido(pedido, cliente, ahora), uow.promociones.obtener_vigentes(ahora)
            )
            pedido.confirmar(c.usuario.usuario_id, cliente, ahora, promocion)
            productos = uow.productos.obtener_por_ids([item.producto_id for item in pedido.lineas])
            ids_ingredientes = {r.ingrediente_id for p in productos.values() for r in p.receta}
            ingredientes = uow.ingredientes.obtener_por_ids(list(ids_ingredientes))
            for linea in pedido.lineas:  # RN-02: la existencia puede haber cambiado desde el alta
                disp = self._disponibilidad.evaluar(
                    productos[linea.producto_id], linea.cantidad, ingredientes
                )
                if not disp.disponible:
                    raise ProductoNoDisponible(disp.motivo)
            self._consumo.descontar(pedido, productos, ingredientes, c.usuario.usuario_id, ahora)
            uow.pedidos.guardar(pedido)
            for ingrediente in ingredientes.values():
                uow.ingredientes.guardar(ingrediente)
                uow.registrar_eventos(ingrediente.extraer_eventos())
            uow.registrar_eventos(pedido.extraer_eventos())
            uow.confirmar()
            return a_dto(pedido)

    def cancelar_pedido(self, c: cmd.CancelarPedido) -> PedidoDto:
        """CU-04 (RN-07, RN-08, RN-09, SP-05, SP-08)."""
        self._exigir(c.usuario, Accion.CANCELAR_PEDIDO)  # SP-05: encargado o gerente
        ahora = self._reloj.ahora()
        with self._uow_factory() as uow:
            pedido = self._obtener_pedido(uow, c.pedido_id)
            estado_previo = pedido.cancelar(c.motivo, c.usuario.usuario_id, ahora)
            if estado_previo is EstadoPedido.CONFIRMADO:  # SP-08: se reintegran los ingredientes
                productos = uow.productos.obtener_por_ids([i.producto_id for i in pedido.lineas])
                ids = {r.ingrediente_id for p in productos.values() for r in p.receta}
                ingredientes = uow.ingredientes.obtener_por_ids(list(ids))
                self._consumo.reintegrar(pedido, productos, ingredientes, c.usuario.usuario_id, ahora)
                for ingrediente in ingredientes.values():
                    uow.ingredientes.guardar(ingrediente)
                    uow.registrar_eventos(ingrediente.extraer_eventos())
            uow.pedidos.guardar(pedido)
            uow.registrar_eventos(pedido.extraer_eventos())
            uow.confirmar()
            return a_dto(pedido)

    def cerrar_pedido(self, c: cmd.CerrarPedido) -> PedidoDto:
        self._exigir(c.usuario, Accion.REGISTRAR_PEDIDOS)
        with self._uow_factory() as uow:
            pedido = self._obtener_pedido(uow, c.pedido_id)
            pedido.cerrar(c.usuario.usuario_id, self._reloj.ahora())
            uow.pedidos.guardar(pedido)
            uow.registrar_eventos(pedido.extraer_eventos())
            uow.confirmar()
            return a_dto(pedido)


class ServicioDeCocina(_ServicioBase):
    """CU-03: preparación por estaciones."""

    def iniciar_preparacion(self, c: cmd.IniciarPreparacion) -> PedidoDto:
        self._exigir(c.usuario, Accion.OPERAR_COCINA)
        with self._uow_factory() as uow:
            pedido = self._obtener_pedido(uow, c.pedido_id)
            pedido.iniciar_preparacion_de_linea(c.linea_id, c.usuario.usuario_id, self._reloj.ahora())
            uow.pedidos.guardar(pedido)
            uow.confirmar()
            return a_dto(pedido)

    def marcar_linea_lista(self, c: cmd.MarcarLineaLista) -> ResultadoMarcarLista:
        self._exigir(c.usuario, Accion.OPERAR_COCINA)
        with self._uow_factory() as uow:
            pedido = self._obtener_pedido(uow, c.pedido_id)
            listo = pedido.marcar_linea_lista(c.linea_id, c.usuario.usuario_id, self._reloj.ahora())
            uow.pedidos.guardar(pedido)
            uow.registrar_eventos(pedido.extraer_eventos())
            uow.confirmar()
            return ResultadoMarcarLista(listo, a_dto(pedido))


class ServicioDeInventario(_ServicioBase):
    """CU-05: existencias e ingredientes críticos."""

    @staticmethod
    def _dto(ingrediente) -> IngredienteDto:
        return IngredienteDto(
            ingrediente.ingrediente_id,
            ingrediente.nombre,
            ingrediente.existencia,
            ingrediente.umbral.cantidad,
            ingrediente.es_critico,
        )

    def _cargar(self, uow, ingrediente_id):
        ingrediente = uow.ingredientes.obtener_por_id(ingrediente_id)
        if ingrediente is None:
            raise RecursoNoEncontrado(f"El ingrediente {ingrediente_id} no existe.")
        return ingrediente

    def registrar_existencia(self, c: cmd.RegistrarExistencia) -> IngredienteDto:
        self._exigir(c.usuario, Accion.GESTIONAR_INVENTARIO)
        with self._uow_factory() as uow:
            ingrediente = self._cargar(uow, c.ingrediente_id)
            ingrediente.registrar_conteo(
                c.cantidad_contada, c.usuario.usuario_id, self._reloj.ahora(), "conteo físico"
            )
            uow.ingredientes.guardar(ingrediente)
            uow.registrar_eventos(ingrediente.extraer_eventos())
            uow.confirmar()
            return self._dto(ingrediente)

    def registrar_movimiento(self, c: cmd.RegistrarMovimiento) -> IngredienteDto:
        self._exigir(c.usuario, Accion.GESTIONAR_INVENTARIO)
        tipo = str(c.tipo).upper()
        if tipo not in ("ENTRADA", "SALIDA"):
            raise DatoInvalido("El tipo de movimiento debe ser ENTRADA o SALIDA")
        with self._uow_factory() as uow:
            ingrediente = self._cargar(uow, c.ingrediente_id)
            ahora = self._reloj.ahora()
            if tipo == "ENTRADA":
                ingrediente.registrar_entrada(c.cantidad, c.usuario.usuario_id, ahora, "manual")
            else:
                ingrediente.registrar_salida(c.cantidad, c.usuario.usuario_id, ahora, "manual")
            uow.ingredientes.guardar(ingrediente)
            uow.registrar_eventos(ingrediente.extraer_eventos())
            uow.confirmar()
            return self._dto(ingrediente)

    def definir_umbral_critico(self, c: cmd.DefinirUmbralCritico) -> IngredienteDto:
        self._exigir(c.usuario, Accion.GESTIONAR_INVENTARIO)
        with self._uow_factory() as uow:
            ingrediente = self._cargar(uow, c.ingrediente_id)
            ingrediente.definir_umbral(UmbralCritico(c.umbral))
            uow.ingredientes.guardar(ingrediente)
            uow.confirmar()
            return self._dto(ingrediente)


class ServicioDeCatalogo(_ServicioBase):
    """CU-02: el encargado marca o reactiva productos agotados."""

    def _cambiar(self, c: cmd.CambiarEstadoDeProducto, agotar: bool):
        self._exigir(c.usuario, Accion.GESTIONAR_CATALOGO)
        with self._uow_factory() as uow:
            producto = uow.productos.obtener_por_id(c.producto_id)
            if producto is None:
                raise RecursoNoEncontrado(f"El producto {c.producto_id} no existe.")
            ahora = self._reloj.ahora()
            if agotar:
                producto.marcar_agotado(c.usuario.usuario_id, ahora)
            else:
                producto.reactivar(c.usuario.usuario_id, ahora)
            uow.productos.guardar(producto)
            uow.registrar_eventos(producto.extraer_eventos())
            uow.confirmar()
            return {"producto_id": producto.producto_id, "agotado": producto.agotado}

    def marcar_producto_agotado(self, c):
        return self._cambiar(c, True)

    def reactivar_producto(self, c):
        return self._cambiar(c, False)


class ServicioDePromociones(_ServicioBase):
    """US-15: configuración de promociones con horario y condiciones."""

    def configurar_promocion(self, c: cmd.ConfigurarPromocion) -> dict:
        self._exigir(c.usuario, Accion.GESTIONAR_PROMOCIONES)
        from datetime import time

        try:
            inicio, fin = time.fromisoformat(c.hora_inicio), time.fromisoformat(c.hora_fin)
        except ValueError as exc:
            raise DatoInvalido("Las horas deben tener formato HH:MM") from exc
        condiciones = []
        if c.total_minimo is not None:
            condiciones.append(TotalMinimo(Decimal(str(c.total_minimo))))
        if c.canales:
            condiciones.append(CanalEn(*c.canales))
        promocion = Promocion(
            c.promocion_id, c.nombre, VentanaHoraria(inicio, fin), condiciones, c.descuento_pct
        )
        with self._uow_factory() as uow:
            uow.promociones.guardar(promocion)
            uow.confirmar()
        return {"promocion_id": promocion.promocion_id, "vigente": promocion.vigente}
