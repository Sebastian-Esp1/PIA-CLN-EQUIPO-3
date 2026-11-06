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

Términos nuevos del PIA (no estaban en la Unidad 2): **Receta**, **Umbral crítico**, **Estado del pedido**, **Beneficio preferente** (regla R2 del docente), **Cliente** (entidad con activo/preferente).
