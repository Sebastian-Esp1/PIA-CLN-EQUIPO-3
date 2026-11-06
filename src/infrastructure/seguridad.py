"""Autorizador por rol (SP-05, SP-09): la autenticación y los roles viven en infraestructura."""

from src.application.ports import Accion, IAutorizador, Rol, Usuario

PERMISOS = {
    Rol.MESERO: {Accion.REGISTRAR_PEDIDOS},
    Rol.COCINERO: {Accion.OPERAR_COCINA},
    Rol.ENCARGADO: {
        Accion.REGISTRAR_PEDIDOS,
        Accion.CANCELAR_PEDIDO,
        Accion.OPERAR_COCINA,
        Accion.GESTIONAR_INVENTARIO,
        Accion.GESTIONAR_CATALOGO,
        Accion.GESTIONAR_PROMOCIONES,
        Accion.CONSULTAR_REPORTES,
        Accion.ADMINISTRAR_DATOS,
    },
    Rol.GERENTE: set(Accion),
}


class AutorizadorPorRol(IAutorizador):
    def puede(self, usuario: Usuario, accion: Accion) -> bool:
        return accion in PERMISOS.get(usuario.rol, set())
