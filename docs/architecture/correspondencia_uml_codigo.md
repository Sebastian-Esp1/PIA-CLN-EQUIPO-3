# Correspondencia entre los diagramas y el código

Los diagramas se verifican contra el código implementado con `tests/unit/test_diagramas.py`, que corre en cada ejecución de pytest y en el pipeline: si un diagrama deja de coincidir con el código, la prueba falla.

| Diagrama | Qué se comprueba contra el código | Resultado |
|---|---|---|
| `dominio` (clases DDD) | Las 15 clases existen en `src/domain`; cada atributo y método dibujado existe; las 6 relaciones de composición (Pedido→LineaPedido, LineaPedido→Modificacion, Pedido→RegistroDeCambio, Pedido→Cancelacion, Producto→RequerimientoIngrediente, Ingrediente→MovimientoInventario) están implementadas | Coincide |
| `estados` | Las 9 transiciones dibujadas son exactamente las de `MAQUINA_PEDIDO` | Coincide |
| `er` | Las 11 tablas dibujadas son exactamente las de `src/infrastructure/modelos.py`; las relaciones con llave foránea real están declaradas con `ForeignKey` | Coincide |
| `secuencia_confirmar` / `secuencia_cancelar` | Participantes y mensajes siguen `ServicioDePedidos.confirmar_pedido` (incluye la re-validación de disponibilidad, RN-02) y `cancelar_pedido` | Coincide |
| `capas` | `src/domain` no importa `application`, `infrastructure`, `api`, SQLAlchemy, FastAPI ni Pydantic | Coincide |

## Aclaraciones sobre cómo se representó el código

- **Relaciones lógicas en el ER.** Tres relaciones no tienen restricción `FOREIGN KEY` en la base de datos y se marcan con la etiqueta `_logica`: `promociones → pedidos` (`pedidos.promocion_id`), `pedidos → ventas_resumen` (modelo de lectura CQRS) y `pedidos → eventos_dominio` (bitácora, usa `agregado_id`). Se dejaron sin llave foránea para que la bitácora y el modelo de lectura no bloqueen la transacción del pedido.
- **Modificaciones y cancelación no son tablas.** En el diagrama de dominio son objetos del agregado `Pedido`; en la base se guardan dentro de otra tabla: `lineas_pedido.modificaciones` (columna JSON) y las columnas `cancel_motivo`, `cancel_usuario` y `cancel_fecha` de `pedidos`. Por eso no aparecen como tablas en el ER.
- **Unidad de trabajo.** En las secuencias el participante es `UnidadDeTrabajoSql`, que implementa el puerto `IUnitOfWork`.
- **Especificaciones.** `puede_procesarse()` y `califica_beneficio()` son funciones de `src/domain/specifications.py` que construyen una `Specification`; el `Pedido` las usa al confirmar.
