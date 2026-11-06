# Glosario de dominio (lenguaje ubicuo)

> Selección de los términos de la Unidad 2 que el código usa literalmente. Si el equipo conserva el glosario completo (26 términos), debe adjuntarse aquí.

| Término | Significado | En el código |
|---|---|---|
| Pedido | Solicitud de un cliente por un canal, con líneas, estado e historial | `Pedido` |
| Línea de pedido | Producto, cantidad, precio, estación, estado de preparación y modificaciones | `LineaPedido` |
| Canal de venta | Mesa, teléfono, WhatsApp o domicilio | `CanalVenta` |
| Modificación / extra | Quitar, cambiar o agregar algo a un producto | `Modificacion` |
| Producto | Algo que se vende; tiene receta y estación | `Producto` |
| Receta | Ingredientes y cantidades de un producto | `RequerimientoIngrediente` |
| Ingrediente | Insumo con existencia y umbral | `Ingrediente` |
| Existencia | Cantidad disponible de un ingrediente | `Ingrediente.existencia` |
| Ingrediente crítico | Existencia ≤ umbral | `Ingrediente.es_critico` |
| Disponibilidad | Producto no agotado y con ingredientes suficientes | `DisponibilidadProductos` |
| Estación | Parrilla, preparación fría, bebidas o empaque | `EstacionCocina` |
| Estado del pedido | Etapa del ciclo de vida | `EstadoPedido` |
| Cancelación | Anulación con motivo, usuario y fecha | `Cancelacion` |
| Historial / trazabilidad | Registro inmutable de cambios | `RegistroDeCambio` |
| Promoción | Descuento con horario y condiciones | `Promocion` |
| Venta | Resumen de un pedido cerrado | `VentaResumen` (lado de lectura) |
| Beneficio preferente | Regla R2 del paquete del docente | `califica_beneficio()` |
