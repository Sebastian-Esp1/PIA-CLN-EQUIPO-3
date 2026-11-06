# Glosario de dominio (lenguaje ubicuo)

Glosario original de la Unidad 2 (`requirements/originales_unidad2/Glosario de dominio.pdf`, 26 términos). La columna *En el código* muestra dónde se usa cada término.

| No. | Término | Definición (Unidad 2) | En el código |
|---|---|---|---|
| 1 | Pedido | Registro formal de una solicitud de un cliente con productos, cantidades, modificaciones y datos para su preparación y entrega | `Pedido` |
| 2 | Canal de venta | Medio por el que se origina un pedido: mesa, teléfono, WhatsApp o domicilio | `CanalVenta` |
| 3 | Producto | Alimento, bebida, paquete o complemento del catálogo | `Producto` |
| 4 | Modificación | Cambio solicitado sobre un producto (eliminar, cambiar o agregar) | `Modificacion` |
| 5 | Extra | Complemento adicional asociado a un producto del pedido | `Modificacion` tipo AGREGAR |
| 6 | Disponibilidad | Condición que determina si un producto puede ofrecerse según las existencias | `DisponibilidadProductos` |
| 7 | Producto agotado | Producto que no puede venderse por falta de ingredientes o insumos | `Producto.agotado` |
| 8 | Ingrediente | Insumo usado para elaborar productos; su existencia influye en la disponibilidad | `Ingrediente` |
| 9 | Ingrediente crítico | Ingrediente cuya existencia alcanzó un límite definido | `Ingrediente.es_critico` |
| 10 | Inventario | Registro de cantidades disponibles de ingredientes e insumos | `Ingrediente.existencia`, `MovimientoInventario` |
| 11 | Estación de cocina | Área de preparación: parrilla, preparación fría, bebidas, empaque | `EstacionCocina` |
| 12 | Estado de preparación | Situación de un producto durante su elaboración hasta que queda listo | `EstadoPreparacion` |
| 13 | Cancelación | Un pedido activo deja de continuar; se conserva motivo, usuario, fecha y hora | `Cancelacion` |
| 14 | Trazabilidad | Poder consultar las acciones sobre un pedido con usuario, fecha y hora | `RegistroDeCambio` |
| 15 | Promoción | Beneficio comercial aplicable si se cumplen condiciones y horarios | `Promocion` |
| 16 | Stakeholder | Persona o grupo con responsabilidades o interés en el sistema | roles del sistema |
| 17 | Venta | Registro derivado de un pedido procesado y cerrado | `VentaResumen` |
| 18–26 | BPMN, compuertas XOR/AND/OR, AS-IS, flujo, evento de inicio/fin, actividad | Términos de notación de procesos | `bpmn_as_is_unidad2.svg`, `bpmn_to_be.bpmn` |

## Términos añadidos en el PIA

No estaban en el glosario de la Unidad 2; el equipo los agregó porque el código y la API los usan.

| No. | Término | Definición | En el código |
|---|---|---|---|
| 27 | Línea de pedido | Renglón de un pedido: un producto con su cantidad, precio, estación y estado de preparación; puede llevar modificaciones | `LineaPedido` |
| 28 | Comanda | Orden de trabajo que recibe una estación de cocina: las líneas confirmadas de uno o más pedidos que debe preparar, con sus modificaciones | consulta `consultar_ordenes_de_estacion`, `GET /cocina/estaciones/{estacion}/ordenes`, `OrdenEstacionOut` |
| 29 | Estado del pedido | Etapa en la que va un pedido: EN_REGISTRO, CONFIRMADO, EN_PREPARACION, LISTO, CERRADO o CANCELADO. Solo se permiten las transiciones de la máquina de estados | `EstadoPedido`, `MAQUINA_PEDIDO` |
| 30 | Receta | Lista de ingredientes y cantidades que consume un producto | `Producto.receta`, `RequerimientoIngrediente` |
| 31 | Umbral crítico | Cantidad mínima de un ingrediente; al alcanzarla se considera crítico | `Ingrediente.umbral`, `UmbralCritico` |
| 32 | Beneficio preferente | Descuento al que tiene derecho un cliente preferente (regla R2 del paquete del docente) | `califica_beneficio()`, `BeneficioPreferenteAplicado` |
| 33 | Cliente | Persona que hace pedidos; puede estar activo o inactivo y ser preferente | `Cliente` |
| 34 | Rol y usuario | Quién opera la API (MESERO, COCINERO, ENCARGADO o GERENTE) y qué acciones le corresponden | `Usuario`, `Rol`, `AutorizadorPorRol` |
| 35 | Movimiento de inventario | Entrada, salida o conteo que cambia la existencia de un ingrediente | `MovimientoInventario` |
| 36 | Evento de dominio | Hecho relevante ya ocurrido (pedido confirmado, producto agotado…) que se registra en la bitácora | `EventoDeDominio` y subclases |
| 37 | Unidad de trabajo | Transacción que guarda todos los cambios de una operación o ninguno | `IUnitOfWork`, `UnidadDeTrabajoSql` |
