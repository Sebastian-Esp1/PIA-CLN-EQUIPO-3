# Matriz de trazabilidad: BRD → regla → historia → caso de uso → componente → prueba

Todas las pruebas están en `tests/` (U = `tests/unit`, I = `tests/integration`). Cobertura total medida: **98.5 %** (ver reporte).

| Necesidad | Regla | US | CU | Componente (código) | Pruebas |
|---|---|---|---|---|---|
| N-01 | RN-01 | US-01, US-03 | CU-01 | `Pedido.iniciar`, `agregar_linea`; `ServicioDePedidos` | U `test_pedido.py::test_iniciar_pedido…`, `test_cantidad_debe_ser_entero_positivo`; I `test_api_flujos.py::test_codigos_http_del_contrato` |
| N-01 | RN-03 | US-02 | CU-01 | `Pedido.agregar_modificacion` | U `test_modificaciones_se_asocian_a_la_linea`; I `test_cu01_modificaciones_extras_por_linea` |
| N-02 | RN-04, RN-08 | US-06 | CU-01 | `Pedido.confirmar`, `puede_procesarse()` | U `test_confirmar_exige_regla_r1…`; I `test_cu01_registrar_y_confirmar…` |
| N-02 | RN-05 | US-07 | CU-03 | `ServicioDeCocina`, `Consultas.consultar_ordenes_de_estacion` | I `test_cu03_cocina_prepara_por_estacion…`, `test_estacion_invalida_es_422` |
| N-02 | RN-06 | US-08 | CU-03 | `Pedido.marcar_linea_lista` | U `test_preparacion_por_linea_y_pedido_listo…` |
| N-03 | RN-02, RN-12 | US-04, US-05 | CU-02 | `DisponibilidadProductos`, `Producto.marcar_agotado` | U `test_disponibilidad_considera…`; I `test_cu02_*`, `test_cantidad_mayor_a_la_existencia…` |
| N-04 | RN-10 | US-09 | CU-05 | `Ingrediente.registrar_*`, `MovimientoInventario` | U `test_entrada_y_salida…`, `test_salida_mayor…`; I `test_cu05_*` |
| N-04 | RN-11 | US-10 | CU-05 | `UmbralCritico`, `IngredienteMarcadoCritico` | U `test_es_critico_es_derivado…`; I `test_cu05_*` |
| N-04 | RN-12 / SP-04 | US-06 | CU-01 | `ConsumoDeIngredientes`, `UnidadDeTrabajoSql` | U `test_consumo_descuenta_y_reintegra…`; I `test_rollback_no_deja_cambios_parciales`, `…_hace_rollback` |
| N-05 | RN-07 | US-11 | CU-04 | `Pedido.cancelar`, `Cancelacion`, `AutorizadorPorRol` | U `test_cancelar_exige_motivo…`; I `test_cu04_*`, `test_matriz_de_roles` |
| N-05 | RN-09 | US-12 | CU-04 | `RegistroDeCambio`, `Consultas.consultar_historial_de_pedido` | U `test_historial_solo_crece…`; I `test_cu01_registrar_y_confirmar…` |
| N-06 | RN-08 / SP-02 | US-04, US-11 | CU-02, CU-04 | `EstadoPedido`, `MaquinaDeEstados` | U `test_transiciones_permitidas`, `test_transiciones_invalidas`, `test_matriz_de_modificacion_y_cancelacion` |
| N-07 | RN-14 | US-13 | — | `VentaRow`, `ActualizadorDeVentas`, evento `PedidoCerrado` | I `test_reportes_de_ventas_y_comparativo`, `test_la_venta_se_registra_una_sola_vez` |
| N-07 | RN-15 | US-14 | — | `ConsultasDeInventarioSql.comparativo` | I `test_reportes_de_ventas_y_comparativo` |
| N-08 | RN-13 | US-15 | CU-01 | `Promocion`, `EvaluadorPromociones` | U `test_promocion_aplica_solo_vigente…`; I `test_cu01_promocion_vigente_aplica_descuento` |
| Paquete docente | R1 | — | — | `puede_procesarse()` (Specification AND) | I `test_casos_de_prueba_del_docente` (60 casos) |
| Paquete docente | R2 | — | — | `califica_beneficio()` (AND/NOT) | I `test_casos_de_prueba_del_docente` (60 casos) |
| Paquete docente | Transiciones | — | — | `MAQUINA_PEDIDO`, API | I `test_transiciones_del_docente` (20 casos) |
| Calidad | — | — | — | Ruff, cobertura, CI | `.github/workflows/ci.yml` |

## Trazabilidad de decisiones
| ADR | Necesidades | Reglas | Evidencia |
|---|---|---|---|
| ADR-01 | N-03, N-05, N-06, N-08 | RN-02, 06, 07, 08, 13 | `src/domain/` |
| ADR-02 | N-02, N-05 | RN-05, 06, 09 | `Pedido`, `test_concurrencia_optimista…` |
| ADR-03 | N-03, N-04 | RN-02, 10, 12, 15 | `ServicioDePedidos.confirmar_pedido` |
| ADR-04 | N-02, N-05, N-07 | RN-14, 15 | `src/application/queries.py` |
| ADR-05..09 | — | — | ver `adr.md` |
