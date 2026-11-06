"""Carga el paquete de datos del docente (CSV) al modelo de dominio del equipo.

Adaptaciones (documentadas en docs/architecture/adaptacion_paquete_docente.md):
- actor -> Cliente; recurso/platillo -> Producto; operación -> Pedido; estado CREADO -> EN_REGISTRO.
- `capacidad_o_stock` de cada platillo se carga como la existencia de un insumo base con receta de
  1 unidad por platillo, para conservar el diseño Producto -> Receta -> Ingrediente del informe U3.
- `habilitado = 0` -> producto agotado. `promocion_activa = 1` -> promoción importada PROMO-DOCENTE.
- La estación de cocina se deduce del nombre del platillo (Hamburguesa/Pasta: parrilla,
  Ensalada: preparación fría, Bebida: bebidas).
"""

import csv
import math
from datetime import datetime, time
from decimal import Decimal
from pathlib import Path

from src.domain.entities import (
    Cliente,
    Ingrediente,
    LineaPedido,
    Pedido,
    Producto,
    Promocion,
)
from src.domain.specifications import TotalMinimo
from src.domain.value_objects import (
    CanalVenta,
    EstacionCocina,
    RegistroDeCambio,
    RequerimientoIngrediente,
    UmbralCritico,
    VentanaHoraria,
)

ESTACION_POR_PALABRA = {
    "hamburguesa": EstacionCocina.PARRILLA,
    "pasta": EstacionCocina.PARRILLA,
    "ensalada": EstacionCocina.PREPARACION_FRIA,
    "bebida": EstacionCocina.BEBIDAS,
}
PROMOCION_DOCENTE = "PROMO-DOCENTE"
USUARIO_IMPORTACION = "importacion-csv"


def leer(directorio, nombre):
    with open(Path(directorio) / nombre, encoding="utf-8-sig", newline="") as archivo:
        return list(csv.DictReader(archivo))


def estacion_de(descripcion: str) -> EstacionCocina:
    palabra = descripcion.strip().split()[0].lower()
    return ESTACION_POR_PALABRA.get(palabra, EstacionCocina.PARRILLA)


def importar(uow_factory, directorio) -> dict:
    """Importa los CSV. Es idempotente: no duplica lo que ya existe. Devuelve un resumen."""
    actores = leer(directorio, "actores.csv")
    catalogo = leer(directorio, "catalogo.csv")
    operaciones = leer(directorio, "operaciones.csv")
    detalle = leer(directorio, "detalle_operaciones.csv")
    resumen = {"clientes": 0, "productos": 0, "pedidos": 0, "lineas": 0}
    with uow_factory() as uow:
        for a in actores:
            if uow.clientes.obtener_por_id(a["actor_id"]) is None:
                uow.clientes.guardar(
                    Cliente(
                        a["actor_id"],
                        a["nombre"],
                        a["activo"] == "1",
                        a["es_preferente"] == "1",
                        a["ciudad"],
                    )
                )
                resumen["clientes"] += 1
        for r in catalogo:
            producto_id = r["recurso_id"]
            if uow.productos.obtener_por_id(producto_id) is not None:
                continue
            existencia = Decimal(r["capacidad_o_stock"])
            ingrediente_id = f"ING-{producto_id}"
            uow.ingredientes.guardar(
                Ingrediente(
                    ingrediente_id,
                    f"Insumo base de {r['descripcion']}",
                    existencia,
                    UmbralCritico(Decimal(math.ceil(existencia * Decimal("0.2")))),
                )
            )
            uow.productos.guardar(
                Producto(
                    producto_id,
                    r["descripcion"],
                    Decimal(r["precio_mxn"]),
                    estacion_de(r["descripcion"]),
                    [RequerimientoIngrediente(ingrediente_id, Decimal(1))],
                    agotado=r["habilitado"] != "1",
                )
            )
            resumen["productos"] += 1
        if uow.promociones.obtener_por_id(PROMOCION_DOCENTE) is None:
            uow.promociones.guardar(
                Promocion(
                    PROMOCION_DOCENTE,
                    "Promoción activa importada del paquete del docente",
                    VentanaHoraria(time(0, 0), time(23, 59)),
                    [TotalMinimo(Decimal("0.01"))],
                    Decimal(0),
                    vigente=False,  # solo marca los pedidos importados; no se aplica a pedidos nuevos
                )
            )
        # Se guardan primero clientes, productos y promoción para respetar las llaves foráneas.
        uow.sesion.flush()
        lineas_por_operacion: dict = {}
        for d in detalle:
            lineas_por_operacion.setdefault(d["operacion_id"], []).append(d)
        productos = uow.productos.obtener_por_ids([r["recurso_id"] for r in catalogo])
        for o in operaciones:
            if uow.pedidos.obtener_por_id(o["operacion_id"]) is not None:
                continue
            creado = datetime.fromisoformat(o["fecha_solicitud"])
            pedido = Pedido(
                o["operacion_id"],
                CanalVenta.MESA,
                o["actor_id"],
                creado,
                autorizado=o["autorizado"] == "1",
                promocion_id=PROMOCION_DOCENTE if o["promocion_activa"] == "1" else None,
            )
            for i, d in enumerate(lineas_por_operacion.get(o["operacion_id"], []), start=1):
                producto = productos[d["recurso_id"]]
                pedido.lineas.append(
                    LineaPedido(
                        i, producto.producto_id, int(d["cantidad"]), producto.precio, producto.estacion
                    )
                )
                resumen["lineas"] += 1
            pedido.historial.append(
                RegistroDeCambio(
                    "Pedido importado", USUARIO_IMPORTACION, creado, f"referencia {o['referencia']}"
                )
            )
            uow.pedidos.agregar(pedido)
            resumen["pedidos"] += 1
        uow.confirmar()
    return resumen
