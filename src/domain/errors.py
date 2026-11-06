"""Errores de dominio expresados en términos de negocio (informe U3, Tabla 29)."""


class ErrorDeDominio(Exception):
    """Base de todos los errores que representan una regla de negocio incumplida."""

    codigo = "ERROR_DE_DOMINIO"
    mensaje_por_defecto = "Se incumplió una regla de negocio."

    def __init__(self, mensaje=None):
        self.mensaje = mensaje or self.mensaje_por_defecto
        super().__init__(self.mensaje)


class DatoInvalido(ErrorDeDominio):
    codigo = "DATO_INVALIDO"
    mensaje_por_defecto = "Los datos enviados no son válidos."


class ProductoNoDisponible(ErrorDeDominio):
    codigo = "PRODUCTO_NO_DISPONIBLE"
    mensaje_por_defecto = "El producto está agotado o le faltan ingredientes."


class PedidoNoModificable(ErrorDeDominio):
    codigo = "PEDIDO_NO_MODIFICABLE"
    mensaje_por_defecto = "El pedido ya no admite cambios en su estado actual."


class PedidoNoProcesable(ErrorDeDominio):
    codigo = "PEDIDO_NO_PROCESABLE"
    mensaje_por_defecto = "El pedido no cumple las precondiciones para procesarse."


class CancelacionNoPermitida(ErrorDeDominio):
    codigo = "CANCELACION_NO_PERMITIDA"
    mensaje_por_defecto = "Este pedido ya no puede cancelarse."


class MotivoDeCancelacionRequerido(ErrorDeDominio):
    codigo = "MOTIVO_REQUERIDO"
    mensaje_por_defecto = "Debe indicar el motivo de la cancelación."


class TransicionDeEstadoInvalida(ErrorDeDominio):
    codigo = "TRANSICION_INVALIDA"
    mensaje_por_defecto = "El pedido no puede pasar a ese estado desde el actual."


class ExistenciaInsuficiente(ErrorDeDominio):
    codigo = "EXISTENCIA_INSUFICIENTE"
    mensaje_por_defecto = "No hay existencia suficiente del ingrediente."


class ConflictoDeConcurrencia(ErrorDeDominio):
    codigo = "CONFLICTO_DE_CONCURRENCIA"
    mensaje_por_defecto = "El registro cambió; vuelva a intentarlo."


class NoAutorizado(ErrorDeDominio):
    codigo = "NO_AUTORIZADO"
    mensaje_por_defecto = "El usuario no tiene permiso para realizar esta operación."


class RecursoNoEncontrado(ErrorDeDominio):
    codigo = "NO_ENCONTRADO"
    mensaje_por_defecto = "El recurso solicitado no existe."
