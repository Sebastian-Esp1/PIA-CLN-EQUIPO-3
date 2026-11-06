"""Aplicación FastAPI: controladores REST delgados que traducen HTTP <-> casos de uso."""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from src.api import esquemas as es
from src.api.contenedor import Contenedor, construir_contenedor
from src.application import commands as cmd
from src.application.ports import Rol, Usuario
from src.domain import errors as er
from src.infrastructure import importacion_csv

DESCRIPCION = """
API REST de **Sazón Urbano**: pedidos, cocina por estaciones, disponibilidad, inventario,
promociones y reportes. Implementa DDD (Pedido, Producto, Ingrediente, Promoción), Specification,
una máquina de estados del pedido y CQRS básico.

**Cómo probarla en Swagger:** todos los endpoints funcionan con los valores por defecto de los
encabezados (`X-Usuario` = `demo`, `X-Rol` = `ENCARGADO`). Cambie `X-Rol` a `MESERO`, `COCINERO` o
`GERENTE` para ver cómo cambian los permisos. Los datos de ejemplo del docente se cargan con
`POST /admin/importar-csv`.

**Códigos de respuesta:** 200/201 éxito · 400 solicitud mal formada · 403 rol sin permiso ·
404 recurso inexistente · 409 regla de negocio o estado incompatible · 422 datos inválidos.
"""

ESTADO_HTTP = {
    er.DatoInvalido: 422,
    er.MotivoDeCancelacionRequerido: 422,
    er.RecursoNoEncontrado: 404,
    er.NoAutorizado: 403,
    er.ProductoNoDisponible: 409,
    er.PedidoNoModificable: 409,
    er.PedidoNoProcesable: 409,
    er.CancelacionNoPermitida: 409,
    er.TransicionDeEstadoInvalida: 409,
    er.ExistenciaInsuficiente: 409,
    er.ConflictoDeConcurrencia: 409,
}
RESPUESTAS_ERROR = {
    403: {"model": es.ErrorOut, "description": "El rol no tiene permiso"},
    404: {"model": es.ErrorOut, "description": "El recurso no existe"},
    409: {"model": es.ErrorOut, "description": "Regla de negocio o estado incompatible"},
    422: {"model": es.ErrorOut, "description": "Datos inválidos"},
}


def _contenedor(request: Request) -> Contenedor:
    return request.app.state.contenedor


def _usuario(
    request: Request,
    x_usuario: str = Header("demo", description="Identificador del usuario que opera"),
    x_rol: str = Header("ENCARGADO", description="MESERO, COCINERO, ENCARGADO o GERENTE"),
    x_api_key: str | None = Header(None, description="Solo si el servidor define API_KEY"),
) -> Usuario:
    clave = _contenedor(request).configuracion.api_key
    if clave and x_api_key != clave:
        raise HTTPException(status_code=401, detail="API key inválida o ausente")
    try:
        return Usuario(x_usuario, Rol(x_rol.upper()))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Rol inválido") from exc


pedidos = APIRouter(prefix="/pedidos", tags=["Pedidos"], responses=RESPUESTAS_ERROR)
cocina = APIRouter(prefix="/cocina", tags=["Cocina"], responses=RESPUESTAS_ERROR)
productos = APIRouter(prefix="/productos", tags=["Productos"], responses=RESPUESTAS_ERROR)
inventario = APIRouter(prefix="/inventario", tags=["Inventario"], responses=RESPUESTAS_ERROR)
promociones = APIRouter(prefix="/promociones", tags=["Promociones"], responses=RESPUESTAS_ERROR)
reportes = APIRouter(prefix="/reportes", tags=["Reportes"], responses=RESPUESTAS_ERROR)
admin = APIRouter(prefix="/admin", tags=["Administración"], responses=RESPUESTAS_ERROR)


# --- Pedidos (CU-01, CU-02, CU-04) ----------------------------------------------------------
@pedidos.post("", response_model=es.PedidoOut, status_code=201, summary="Iniciar pedido (CU-01)")
def iniciar_pedido(datos: es.PedidoIn, request: Request, usuario: Usuario = Depends(_usuario)):
    return _contenedor(request).pedidos.iniciar_pedido(
        cmd.IniciarPedido(datos.canal, datos.cliente_id, usuario)
    )


@pedidos.get("", response_model=list[es.PedidoOut], summary="Listar pedidos")
def listar_pedidos(
    request: Request,
    estado: str | None = Query(None, examples=["EN_REGISTRO"]),
    limite: int = Query(50, ge=1, le=500),
):
    return _contenedor(request).consultas.listar_pedidos(estado, limite)


@pedidos.get("/{pedido_id}", response_model=es.PedidoOut, summary="Consultar un pedido")
def consultar_pedido(pedido_id: str, request: Request):
    return _contenedor(request).consultas.consultar_pedido(pedido_id)


@pedidos.post(
    "/{pedido_id}/lineas",
    response_model=es.LineaAgregadaOut,
    status_code=201,
    summary="Agregar producto (CU-01 / CU-02: rechaza si no hay disponibilidad)",
)
def agregar_producto(
    pedido_id: str, datos: es.LineaIn, request: Request, usuario: Usuario = Depends(_usuario)
):
    resultado = _contenedor(request).pedidos.agregar_producto_al_pedido(
        cmd.AgregarProductoAlPedido(pedido_id, datos.producto_id, datos.cantidad, usuario)
    )
    if not resultado.agregado:  # la incidencia ya quedó registrada en el historial (RN-02)
        return JSONResponse(
            status_code=409,
            content={"codigo": er.ProductoNoDisponible.codigo, "mensaje": resultado.motivo},
        )
    return resultado


@pedidos.post(
    "/{pedido_id}/lineas/{linea_id}/modificaciones",
    response_model=es.PedidoOut,
    status_code=201,
    summary="Agregar modificación o extra a una línea (RN-03)",
)
def agregar_modificacion(
    pedido_id: str,
    linea_id: int,
    datos: es.ModificacionIn,
    request: Request,
    usuario: Usuario = Depends(_usuario),
):
    return _contenedor(request).pedidos.agregar_modificacion(
        cmd.AgregarModificacion(pedido_id, linea_id, datos.tipo, datos.descripcion, usuario)
    )


@pedidos.post("/{pedido_id}/autorizar", response_model=es.PedidoOut, summary="Autorizar pedido")
def autorizar_pedido(pedido_id: str, request: Request, usuario: Usuario = Depends(_usuario)):
    return _contenedor(request).pedidos.autorizar_pedido(cmd.AutorizarPedido(pedido_id, usuario))


@pedidos.post(
    "/{pedido_id}/confirmar",
    response_model=es.PedidoOut,
    summary="Confirmar pedido y enviarlo a cocina (CU-01)",
)
def confirmar_pedido(pedido_id: str, request: Request, usuario: Usuario = Depends(_usuario)):
    return _contenedor(request).pedidos.confirmar_pedido(cmd.ConfirmarPedido(pedido_id, usuario))


@pedidos.post(
    "/{pedido_id}/cancelar",
    response_model=es.PedidoOut,
    summary="Cancelar pedido con motivo (CU-04)",
)
def cancelar_pedido(
    pedido_id: str, datos: es.CancelacionIn, request: Request, usuario: Usuario = Depends(_usuario)
):
    return _contenedor(request).pedidos.cancelar_pedido(
        cmd.CancelarPedido(pedido_id, datos.motivo, usuario)
    )


@pedidos.post("/{pedido_id}/cerrar", response_model=es.PedidoOut, summary="Cerrar (entregar) pedido")
def cerrar_pedido(pedido_id: str, request: Request, usuario: Usuario = Depends(_usuario)):
    return _contenedor(request).pedidos.cerrar_pedido(cmd.CerrarPedido(pedido_id, usuario))


@pedidos.get(
    "/{pedido_id}/historial",
    response_model=list[es.HistorialOut],
    summary="Historial de cambios del pedido (US-12)",
)
def historial(pedido_id: str, request: Request):
    return _contenedor(request).consultas.consultar_historial_de_pedido(pedido_id)


# --- Cocina (CU-03) -------------------------------------------------------------------------
@cocina.get(
    "/estaciones/{estacion}/ordenes",
    response_model=list[es.OrdenEstacionOut],
    summary="Órdenes de una estación (US-07)",
)
def ordenes_de_estacion(estacion: str, request: Request):
    return _contenedor(request).consultas.consultar_ordenes_de_estacion(estacion)


@cocina.post(
    "/pedidos/{pedido_id}/lineas/{linea_id}/iniciar",
    response_model=es.PedidoOut,
    summary="Iniciar preparación de una línea",
)
def iniciar_preparacion(
    pedido_id: str, linea_id: int, request: Request, usuario: Usuario = Depends(_usuario)
):
    return _contenedor(request).cocina.iniciar_preparacion(
        cmd.IniciarPreparacion(pedido_id, linea_id, usuario)
    )


@cocina.post(
    "/pedidos/{pedido_id}/lineas/{linea_id}/listo",
    response_model=es.LineaListaOut,
    summary="Marcar línea como lista (US-08)",
)
def marcar_linea_lista(
    pedido_id: str, linea_id: int, request: Request, usuario: Usuario = Depends(_usuario)
):
    return _contenedor(request).cocina.marcar_linea_lista(
        cmd.MarcarLineaLista(pedido_id, linea_id, usuario)
    )


# --- Productos (CU-02) ----------------------------------------------------------------------
@productos.get(
    "/disponibilidad",
    response_model=list[es.DisponibilidadOut],
    summary="Disponibilidad de productos (US-04)",
)
def disponibilidad(request: Request):
    return _contenedor(request).consultas.consultar_disponibilidad_de_productos()


@productos.post("/{producto_id}/agotar", response_model=es.ProductoEstadoOut, summary="Marcar agotado (US-05)")
def agotar(producto_id: str, request: Request, usuario: Usuario = Depends(_usuario)):
    return _contenedor(request).catalogo.marcar_producto_agotado(
        cmd.CambiarEstadoDeProducto(producto_id, usuario)
    )


@productos.post("/{producto_id}/reactivar", response_model=es.ProductoEstadoOut, summary="Reactivar producto (US-05)")
def reactivar(producto_id: str, request: Request, usuario: Usuario = Depends(_usuario)):
    return _contenedor(request).catalogo.reactivar_producto(
        cmd.CambiarEstadoDeProducto(producto_id, usuario)
    )


# --- Inventario (CU-05) ---------------------------------------------------------------------
@inventario.get("/ingredientes", response_model=list[es.IngredienteOut], summary="Existencias")
def ingredientes(request: Request):
    return _contenedor(request).consultas.consultar_ingredientes()


@inventario.get(
    "/criticos", response_model=list[es.CriticoOut], summary="Ingredientes críticos (US-10)"
)
def criticos(request: Request):
    return _contenedor(request).consultas.consultar_ingredientes_criticos()


@inventario.post(
    "/ingredientes/{ingrediente_id}/movimientos",
    response_model=es.IngredienteOut,
    summary="Registrar entrada o salida (US-09)",
)
def movimiento(
    ingrediente_id: str, datos: es.MovimientoIn, request: Request, usuario: Usuario = Depends(_usuario)
):
    return _contenedor(request).inventario.registrar_movimiento(
        cmd.RegistrarMovimiento(ingrediente_id, datos.tipo, datos.cantidad, usuario)
    )


@inventario.post(
    "/ingredientes/{ingrediente_id}/conteo",
    response_model=es.IngredienteOut,
    summary="Registrar conteo físico (US-09)",
)
def conteo(
    ingrediente_id: str, datos: es.ConteoIn, request: Request, usuario: Usuario = Depends(_usuario)
):
    return _contenedor(request).inventario.registrar_existencia(
        cmd.RegistrarExistencia(ingrediente_id, datos.cantidad_contada, usuario)
    )


@inventario.put(
    "/ingredientes/{ingrediente_id}/umbral",
    response_model=es.IngredienteOut,
    summary="Definir umbral crítico (SP-03)",
)
def umbral(
    ingrediente_id: str, datos: es.UmbralIn, request: Request, usuario: Usuario = Depends(_usuario)
):
    return _contenedor(request).inventario.definir_umbral_critico(
        cmd.DefinirUmbralCritico(ingrediente_id, datos.umbral, usuario)
    )


# --- Promociones (US-15) --------------------------------------------------------------------
@promociones.post("", response_model=es.PromocionOut, status_code=201, summary="Configurar promoción")
def configurar_promocion(datos: es.PromocionIn, request: Request, usuario: Usuario = Depends(_usuario)):
    return _contenedor(request).promociones.configurar_promocion(
        cmd.ConfigurarPromocion(
            datos.promocion_id,
            datos.nombre,
            datos.hora_inicio,
            datos.hora_fin,
            datos.total_minimo,
            datos.canales,
            datos.descuento_pct,
            usuario,
        )
    )


# --- Reportes (US-13, US-14) ----------------------------------------------------------------
def _rango(desde: datetime, hasta: datetime):
    if desde > hasta:
        raise HTTPException(status_code=400, detail="'desde' no puede ser posterior a 'hasta'")


@reportes.get("/ventas", response_model=list[es.VentaOut], summary="Ventas por periodo (US-13)")
def ventas(
    request: Request,
    desde: datetime = Query(examples=["2026-01-01T00:00:00"]),
    hasta: datetime = Query(examples=["2026-12-31T23:59:59"]),
    usuario: Usuario = Depends(_usuario),
):
    _rango(desde, hasta)
    return _contenedor(request).consultas.consultar_ventas_por_periodo(usuario, desde, hasta)


@reportes.get(
    "/comparativo-inventario",
    response_model=list[es.ComparativoOut],
    summary="Comparativo ventas vs. inventario (US-14)",
)
def comparativo(
    request: Request,
    desde: datetime = Query(examples=["2026-01-01T00:00:00"]),
    hasta: datetime = Query(examples=["2026-12-31T23:59:59"]),
    usuario: Usuario = Depends(_usuario),
):
    _rango(desde, hasta)
    return _contenedor(request).consultas.consultar_comparativo_ventas_inventario(
        usuario, desde, hasta
    )


# --- Administración -------------------------------------------------------------------------
@admin.post(
    "/importar-csv",
    response_model=es.ImportacionOut,
    summary="Cargar el paquete de datos del docente (idempotente)",
)
def importar_csv(request: Request, usuario: Usuario = Depends(_usuario)):
    from src.application.ports import Accion
    from src.infrastructure.seguridad import AutorizadorPorRol

    if not AutorizadorPorRol().puede(usuario, Accion.ADMINISTRAR_DATOS):
        raise er.NoAutorizado()
    c = _contenedor(request)
    return importacion_csv.importar(c.uow_factory, c.configuracion.data_dir)


def crear_app(contenedor: Contenedor | None = None) -> FastAPI:
    @asynccontextmanager
    async def vida(app: FastAPI):
        c = app.state.contenedor
        if c.configuracion.seed_on_start:
            importacion_csv.importar(c.uow_factory, c.configuracion.data_dir)
        yield

    app = FastAPI(
        title="Sazón Urbano · API de lógica de negocio",
        description=DESCRIPCION,
        version="1.0.0",
        lifespan=vida,
    )
    app.state.contenedor = contenedor or construir_contenedor()

    @app.exception_handler(er.ErrorDeDominio)
    async def manejar_error_de_dominio(_: Request, exc: er.ErrorDeDominio):
        estado = next((c for t, c in ESTADO_HTTP.items() if type(exc) is t), 409)
        return JSONResponse(status_code=estado, content={"codigo": exc.codigo, "mensaje": exc.mensaje})

    @app.get("/health", tags=["Sistema"], summary="Estado del servicio")
    def health():
        return {"estado": "ok"}

    for router in (pedidos, cocina, productos, inventario, promociones, reportes, admin):
        app.include_router(router)
    return app

