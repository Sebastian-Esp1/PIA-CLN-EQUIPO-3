"""Textos en lenguaje de negocio para la documentación interactiva (Swagger).

Cada entrada es ``nombre_de_la_función: (título, explicación, respuesta exitosa)``.
La ruta técnica no cambia; solo cómo se describe para quien no es programador.
"""

TEXTOS: dict[str, tuple[str, str, str]] = {
    "iniciar_pedido": (
        "Abrir un pedido nuevo",
        "Crea un pedido vacío para un cliente. Después se le agregan productos.\n\n"
        "**Quién puede:** mesero, encargado o gerente. *(Caso de uso CU-01)*",
        "Pedido creado",
    ),
    "listar_pedidos": (
        "Ver la lista de pedidos",
        "Muestra los pedidos más recientes. Se puede filtrar por etapa (por ejemplo `EN_REGISTRO`).",
        "Lista de pedidos",
    ),
    "consultar_pedido": (
        "Ver un pedido",
        "Muestra el detalle de un pedido: productos, totales, descuento y etapa en la que va.",
        "Detalle del pedido",
    ),
    "agregar_producto": (
        "Agregar un producto al pedido",
        "Suma un platillo o bebida al pedido. Si el producto está agotado o falta algún ingrediente, "
        "no se agrega y se explica el motivo. *(CU-01 y CU-02)*",
        "Resultado de agregar el producto",
    ),
    "agregar_modificacion": (
        "Pedir un cambio o extra en un producto",
        "Registra una indicación para cocina, por ejemplo «sin cebolla» o «extra queso».",
        "Pedido con la indicación registrada",
    ),
    "autorizar_pedido": (
        "Autorizar un pedido",
        "El encargado da el visto bueno para que el pedido pueda confirmarse.",
        "Pedido autorizado",
    ),
    "confirmar_pedido": (
        "Confirmar y mandar a cocina",
        "Confirma el pedido, descuenta los ingredientes del inventario y lo envía a cocina. "
        "Todo ocurre junto: si algo falla, no se cambia nada. *(CU-01)*",
        "Pedido confirmado",
    ),
    "cancelar_pedido": (
        "Cancelar un pedido",
        "Cancela el pedido y devuelve los ingredientes al inventario. Es obligatorio escribir el motivo. "
        "El mesero **no** puede cancelar un pedido ya confirmado; el encargado sí. *(CU-04)*",
        "Pedido cancelado",
    ),
    "cerrar_pedido": (
        "Entregar y cerrar el pedido",
        "Marca el pedido como entregado al cliente y lo cuenta como venta.",
        "Pedido cerrado",
    ),
    "historial": (
        "Ver quién cambió qué en un pedido",
        "Muestra cada cambio del pedido con quién lo hizo, cuándo y por qué. *(US-12)*",
        "Historial del pedido",
    ),
    "ordenes_de_estacion": (
        "Ver qué debe preparar una estación de cocina",
        "Lista lo pendiente de una estación: `PARRILLA`, `PREPARACION_FRIA`, `BEBIDAS` o `EMPAQUE`. *(US-07)*",
        "Órdenes pendientes de la estación",
    ),
    "iniciar_preparacion": (
        "Empezar a preparar un producto",
        "El cocinero avisa que ya comenzó con una línea del pedido.",
        "Línea en preparación",
    ),
    "marcar_linea_lista": (
        "Avisar que un producto está listo",
        "Marca la línea como lista. Cuando todas lo están, el pedido completo queda listo. *(US-08)*",
        "Línea marcada como lista",
    ),
    "disponibilidad": (
        "Ver qué productos se pueden vender hoy",
        "Indica, para cada producto, si hay ingredientes suficientes y por qué sí o por qué no. *(US-04)*",
        "Disponibilidad de cada producto",
    ),
    "agotar": (
        "Marcar un producto como agotado",
        "Deja de ofrecer el producto hasta que se reactive. *(US-05)*",
        "Producto marcado como agotado",
    ),
    "reactivar": (
        "Volver a ofrecer un producto",
        "Quita la marca de agotado para poder venderlo otra vez. *(US-05)*",
        "Producto reactivado",
    ),
    "ingredientes": (
        "Ver cuánto hay de cada ingrediente",
        "Muestra las existencias de bodega y cuáles están en el mínimo permitido.",
        "Existencias de ingredientes",
    ),
    "criticos": (
        "Ver qué ingredientes se están acabando",
        "Muestra solo los ingredientes en o por debajo de su mínimo y qué productos "
        "se verían afectados. *(US-10)*",
        "Ingredientes en riesgo",
    ),
    "movimiento": (
        "Registrar entrada o salida de un ingrediente",
        "Suma lo que llegó de un proveedor (`ENTRADA`) o resta lo que salió o se echó a perder "
        "(`SALIDA`). *(US-09)*",
        "Existencia actualizada",
    ),
    "conteo": (
        "Registrar el conteo físico",
        "Cuando se cuenta la bodega, deja la existencia exactamente en la cantidad contada. *(US-09)*",
        "Existencia actualizada",
    ),
    "umbral": (
        "Cambiar el mínimo de un ingrediente",
        "Define a partir de qué cantidad el ingrediente se considera en riesgo.",
        "Mínimo actualizado",
    ),
    "configurar_promocion": (
        "Crear una promoción",
        "Define un descuento con horario, canales y monto mínimo de compra. *(US-15)*",
        "Promoción creada",
    ),
    "ventas": (
        "Consultar ventas de un periodo",
        "Lista los pedidos entregados entre dos fechas con su importe. Solo gerente. *(US-13)*",
        "Ventas del periodo",
    ),
    "comparativo": (
        "Comparar ventas contra inventario",
        "Muestra, por ingrediente, lo que debería haber según las ventas y lo que se contó. "
        "Un número negativo significa faltante. *(US-14)*",
        "Comparativo por ingrediente",
    ),
    "importar_csv": (
        "Cargar los datos de ejemplo",
        "Carga clientes, productos y pedidos de ejemplo. Se puede repetir sin duplicar datos. "
        "Solo gerente.",
        "Datos cargados",
    ),
}


def aplicar_textos(router) -> None:
    """Reemplaza título, descripción y texto de respuesta de cada ruta del router."""
    for ruta in router.routes:
        if ruta.name in TEXTOS:
            ruta.summary, ruta.description, ruta.response_description = TEXTOS[ruta.name]
