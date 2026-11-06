# Adaptación del paquete del docente al modelo propio

El LEEME del paquete indica que su flujo y sus reglas son un **modelo de pruebas propuesto**, no un requerimiento, y que si difieren
del BRD/US/BPMN/DDD del equipo se deben **documentar las diferencias y adaptar fixtures y oráculos**. Esta es esa documentación.

| Tema | Paquete del docente | Modelo del equipo (U2/U3) | Adaptación |
|---|---|---|---|
| Actor | `actores.csv` (comensal activo/preferente, ciudad) | Cliente + usuarios con rol | Entidad `Cliente` (activo, preferente). Los roles son usuarios del sistema, no clientes |
| Recurso | `catalogo.csv` (precio, `capacidad_o_stock`, `habilitado`) | Producto con receta de ingredientes y estación | `Producto` con receta de **1 insumo base** (`ING-<producto>`); `capacidad_o_stock` = existencia inicial; `habilitado=0` → producto agotado; estación inferida por descripción |
| Operación | CREADO → ACEPTADO → EN_PREPARACION → ENTREGADO; CANCELADO | EN_REGISTRO → CONFIRMADO → EN_PREPARACION → LISTO → CERRADO; CANCELADO | Se mantiene la máquina propia (SP-01). Equivalencias: CREADO≈EN_REGISTRO, ACEPTADO≈CONFIRMADO, ENTREGADO≈CERRADO |
| Acciones de transición | aprobar, completar, cancelar, repetir_aprobacion, saltar_estado | confirmar, preparar→listo→cerrar, cancelar | aprobar = confirmar; completar = confirmar + preparar y marcar listas todas las líneas + cerrar; saltar_estado = cerrar desde EN_REGISTRO (409 TRANSICION_INVALIDA) |
| R1 `puede_procesarse` | actor activo AND ≥1 línea AND autorizado | RN-01 y RN-04 | Specification `puede_procesarse()` y precondición de `Pedido.confirmar` |
| R2 `beneficio_referencia` | preferente AND total ≥ 1500 AND NOT promoción | RN-13 (promoción) | Specification `califica_beneficio()`; se aplica al confirmar como `beneficio_aplicado`; no sustituye la promoción propia |
| Precios | Importes MXN | SP-06: sin precios | **Revisión de SP-06** (ADR-08) |
| Disponibilidad | `capacidad_o_stock` | RN-02/RN-12 existencias de receta | Disponible = no agotado y existencia ≥ cantidad solicitada |
| Autorización | columna `autorizado` por operación | SP-05/SP-09 roles | Se conserva `autorizado` como atributo del pedido (`POST /pedidos/{id}/autorizar`) además de la matriz de roles |
| Promoción activa | columna `promocion_activa` | Aggregate Promoción | Se importa como `promocion_id` con una promoción docente no vigente (0 %), solo para marcar los pedidos importados |
| Canal | no existe | RN-01 exige canal | Los pedidos importados se registran con canal `MESA` |
| Estado inicial | CREADO | EN_REGISTRO | Todos los pedidos importados arrancan en EN_REGISTRO; los cambios solo ocurren por código |
| Códigos HTTP | 200/201, 400/409/422, 404 | Contrato propio | 201 creación; 200 acciones; 400 rango/rol inválido; 401 API key; 403 rol; 404 inexistente; 409 regla/estado; 422 datos inválidos |

## Oráculos independientes
`tests/integration/test_paquete_docente.py` recalcula desde los CSV, **sin usar el dominio**:
- total = Σ precio × cantidad con `Decimal`;
- R1 = actor activo ∧ detalle no vacío ∧ autorizado;
- R2 = preferente ∧ total ≥ 1500 ∧ ¬promoción;
- éxito de `aprobar` = R1 ∧ todos los productos habilitados con existencia suficiente.

Resultado: **120/120 casos** y **20/20 transiciones** coinciden con el oráculo; hay casos positivos y negativos de cada regla.
