# Historias de usuario US-01..US-15 con criterios Gherkin

> **Procedencia.** Historias US-01..US-15 de la Unidad 2 (`originales_unidad2/User Story.pdf`). El enunciado «Como…
> quiero… para…» es el original; los criterios Gherkin se detallaron para que sean ejecutables contra la API (los originales
> son un Given/When/Then por historia, que aquí se amplían con escenarios de error). Nota: en el PDF original, el *story mapping*
> de US-02 menciona promociones; por su enunciado y criterio corresponde a modificaciones y extras, y así se implementó.

Formato: *Como* <rol> *quiero* <acción> *para* <beneficio>. Cada historia indica sus reglas (RN), caso de uso (CU), la prueba
que la verifica y el endpoint.

---
## US-01 Registrar un pedido con productos y cantidades
**Como** mesero/cajero **quiero** registrar un pedido con productos y cantidades **para** que la orden quede correctamente capturada. (RN-01, CU-01, N-01)
```gherkin
Escenario: Iniciar pedido con canal válido
  Dado un cliente existente y un usuario con rol MESERO
  Cuando inicia un pedido con canal "MESA"
  Entonces el pedido queda en estado "EN_REGISTRO" con su historial inicial
Escenario: Canal inválido
  Cuando inicia un pedido con canal "MOSTRADOR"
  Entonces el sistema responde 422 DATO_INVALIDO
```
Prueba: `test_pedido.py::test_iniciar_pedido_registra_historial_y_evento`, `test_api_flujos.py::test_codigos_http_del_contrato` · `POST /pedidos`

## US-02 Agregar modificaciones y extras
**Como** mesero **quiero** asociar "sin cebolla" o "extra queso" a un producto **para** que cocina lo vea. (RN-03, CU-01)
```gherkin
Escenario: Modificación asociada a la línea
  Dado un pedido en registro con una línea
  Cuando agrego la modificación QUITAR "sin cebolla" a la línea 1
  Entonces la línea muestra la modificación y queda en el historial
Escenario: Tipo de modificación inválido
  Cuando agrego la modificación BORRAR
  Entonces el sistema responde 422
```
Prueba: `test_pedido.py::test_modificaciones_se_asocian_a_la_linea`, `test_api_flujos.py::test_cu01_modificaciones_extras_por_linea` · `POST /pedidos/{id}/lineas/{n}/modificaciones`

## US-03 Seleccionar el canal de venta
**Como** mesero/cajero **quiero** seleccionar el canal (mesa, teléfono, WhatsApp o domicilio) **para** identificar su origen. (RN-01, CU-01)
```gherkin
Escenario: Canal válido
  Cuando inicio un pedido con canal "WHATSAPP"
  Entonces el canal queda guardado en el pedido
Escenario: Cantidad válida (US-01)
  Cuando agrego 2 unidades de un producto disponible
  Entonces el total del pedido es 2 x precio
Escenario: Cantidad cero o negativa
  Cuando agrego 0 unidades
  Entonces el sistema responde 422 DATO_INVALIDO
```
Prueba: `test_pedido.py::test_canal_invalido_se_rechaza`, `test_cantidad_debe_ser_entero_positivo`, `test_api_flujos.py::test_codigos_http_del_contrato` · `POST /pedidos`, `POST /pedidos/{id}/lineas`

## US-04 Rechazar productos no disponibles
**Como** mesero **quiero** que el sistema rechace un producto agotado **para** no vender lo que no se puede preparar. (RN-02, RN-12, CU-02, N-03, N-06)
```gherkin
Escenario: Producto agotado
  Dado un producto marcado como agotado
  Cuando intento agregarlo al pedido
  Entonces el sistema responde 409 PRODUCTO_NO_DISPONIBLE
  Y la línea no se agrega
  Y queda una incidencia en el historial del pedido
Escenario: Existencia insuficiente
  Dado un producto con 13 unidades de existencia
  Cuando intento agregar 999 unidades
  Entonces el sistema responde 409
```
Prueba: `test_api_flujos.py::test_cu02_producto_agotado_se_rechaza_y_deja_incidencia`, `test_cantidad_mayor_a_la_existencia_no_se_agrega` · `POST /pedidos/{id}/lineas`

## US-05 Marcar y reactivar productos agotados
**Como** encargado **quiero** marcar un producto como agotado y reactivarlo **para** reflejar la realidad de la cocina. (RN-02, CU-02)
```gherkin
Escenario: Agotar y reactivar
  Cuando el encargado marca el producto como agotado
  Entonces no puede agregarse a pedidos
  Cuando lo reactiva
  Entonces vuelve a poder agregarse
Escenario: Rol sin permiso
  Cuando un mesero intenta marcarlo agotado
  Entonces el sistema responde 403
```
Prueba: `test_api_flujos.py::test_cu02_agotar_y_reactivar_producto`, `test_matriz_de_roles` · `POST /productos/{id}/agotar|reactivar`

## US-06 Enviar el pedido confirmado a cocina
**Como** mesero **quiero** confirmar el pedido **para** que cocina lo reciba completo. (RN-04, RN-08, SP-04, CU-01, N-02)
```gherkin
Escenario: Confirmación exitosa
  Dado un pedido autorizado, con líneas y cliente activo
  Cuando lo confirmo
  Entonces pasa a "CONFIRMADO" y se descuentan los ingredientes de su receta en la misma transacción
Escenario: Pedido no procesable
  Dado un pedido sin autorización, sin líneas o de un cliente inactivo
  Cuando lo confirmo
  Entonces responde 409 PEDIDO_NO_PROCESABLE y no cambia nada
Escenario: Existencia insuficiente al confirmar
  Entonces responde 409 y el inventario queda igual (rollback)
```
Prueba: `test_api_flujos.py::test_cu01_registrar_y_confirmar...`, `..._409`, `..._rollback` · `POST /pedidos/{id}/confirmar`

## US-07 Ver solo los productos de mi estación
**Como** cocinero **quiero** ver las órdenes de mi estación **para** preparar lo que me corresponde. (RN-05, CU-03, N-02)
```gherkin
Escenario: Consulta por estación
  Dado un pedido confirmado con una hamburguesa
  Cuando consulto la estación PARRILLA
  Entonces veo esa línea y sus modificaciones
Escenario: Estación inválida
  Cuando consulto la estación "PATIO"
  Entonces el sistema responde 422
```
Prueba: `test_api_flujos.py::test_cu03_cocina_prepara_por_estacion...`, `test_estacion_invalida_es_422` · `GET /cocina/estaciones/{estacion}/ordenes`

## US-08 Marcar productos como listos
**Como** cocinero **quiero** marcar mi producto como listo **para** que el pedido se complete cuando todas las partes estén listas. (RN-06, CU-03)
```gherkin
Escenario: Pedido listo solo al terminar todas las líneas
  Dado un pedido con 2 líneas en preparación
  Cuando se marca lista la primera
  Entonces el pedido sigue "EN_PREPARACION"
  Cuando se marca lista la segunda
  Entonces el pedido pasa a "LISTO"
```
Prueba: `test_pedido.py::test_preparacion_por_linea_y_pedido_listo_al_terminar_todas` · `POST /cocina/pedidos/{id}/lineas/{n}/listo`

## US-09 Registrar existencias e inventario
**Como** encargado **quiero** registrar entradas, salidas y conteos **para** que la existencia sea confiable. (RN-10, CU-05, N-04)
```gherkin
Escenario: Movimientos
  Cuando registro una entrada de 4 y una salida de 1
  Entonces la existencia cambia en +3 y cada movimiento queda registrado
Escenario: Salida mayor a la existencia
  Entonces responde 409 y la existencia no cambia
```
Prueba: `test_ingrediente_producto_promocion.py::test_entrada_y_salida...`, `test_api_flujos.py::test_cu05_movimientos_conteo_umbral_y_criticos` · `POST /inventario/ingredientes/{id}/movimientos|conteo`

## US-10 Detectar ingredientes críticos
**Como** encargado **quiero** saber qué ingredientes están por agotarse y qué productos afectan **para** reabastecer a tiempo. (RN-11, SP-03, CU-05)
```gherkin
Escenario: Cruce del umbral
  Dado un ingrediente con umbral 3 y existencia 5
  Cuando una salida deja la existencia en 3
  Entonces se marca crítico y se emite IngredienteMarcadoCritico una sola vez
  Y aparece en /inventario/criticos con los productos afectados
```
Prueba: `test_es_critico_es_derivado_y_el_evento_se_emite_solo_al_cruzar`, `test_cu05_...` · `GET /inventario/criticos`, `PUT .../umbral`

## US-11 Cancelar un pedido con motivo
**Como** encargado **quiero** cancelar un pedido indicando el motivo **para** dejar constancia. (RN-07, RN-08, SP-02, SP-05, SP-08, CU-04, N-05, N-06)
```gherkin
Escenario: Cancelación válida
  Dado un pedido confirmado
  Cuando el encargado lo cancela con motivo "cliente se fue"
  Entonces queda "CANCELADO" con motivo, usuario, fecha y hora, y se reintegran los ingredientes
Escenario: Sin motivo
  Entonces responde 422 MOTIVO_REQUERIDO
Escenario: Estado no cancelable (Listo o Cerrado)
  Entonces responde 409 CANCELACION_NO_PERMITIDA
Escenario: Usuario no autorizado
  Cuando un mesero intenta cancelar
  Entonces responde 403
```
Prueba: `test_api_flujos.py::test_cu04_*`, `test_pedido.py::test_cancelar_*`, `test_no_se_cancela_en_estados_finales_o_listo` · `POST /pedidos/{id}/cancelar`

## US-12 Consultar el historial de un pedido
**Como** encargado **quiero** ver quién hizo cada cambio y cuándo **para** auditar. (RN-09, N-05)
```gherkin
Escenario: Historial inmutable y ordenado
  Dado un pedido iniciado, con línea, autorizado y confirmado
  Cuando consulto su historial
  Entonces veo las acciones en orden con usuario y fecha
```
Prueba: `test_pedido.py::test_historial_solo_crece_y_conserva_orden`, `test_api_flujos.py::test_cu01_registrar_y_confirmar...` · `GET /pedidos/{id}/historial`

## US-13 Consultar ventas por periodo
**Como** gerente **quiero** ver las ventas entre dos fechas **para** evaluar el negocio. (RN-14, N-07)
```gherkin
Escenario: Venta a partir de un pedido cerrado
  Dado un pedido cerrado con 2 unidades
  Cuando el gerente consulta el periodo
  Entonces aparece una sola venta con unidades e importe
Escenario: Rango invertido
  Entonces responde 400
Escenario: Rol sin permiso
  Entonces responde 403
```
Prueba: `test_api_flujos.py::test_reportes_de_ventas_y_comparativo`, `test_infraestructura.py::test_la_venta_se_registra_una_sola_vez` · `GET /reportes/ventas`

## US-14 Comparar ventas contra inventario
**Como** gerente **quiero** ver diferencias entre inventario esperado y registrado **para** detectar mermas. (RN-15, N-04, N-07)
```gherkin
Escenario: Comparativo
  Cuando el gerente consulta el comparativo del periodo
  Entonces recibe por ingrediente el consumo esperado según ventas y el registrado, con su diferencia
```
Prueba: `test_api_flujos.py::test_reportes_de_ventas_y_comparativo` · `GET /reportes/comparativo-inventario`

## US-15 Configurar y aplicar promociones
**Como** gerente **quiero** configurar promociones con horario y condiciones **para** aplicarlas automáticamente. (RN-13, N-08)
```gherkin
Escenario: Promoción vigente y dentro de horario
  Dado una promoción 00:00-23:59 con total mínimo 100 y 10 % de descuento
  Cuando se confirma un pedido de 580
  Entonces se aplica la promoción: descuento 58.00, total a pagar 522.00
Escenario: Fuera de horario o sin cumplir condiciones
  Entonces no se aplica
Escenario: Horario inválido
  Cuando inicio es posterior al fin
  Entonces responde 422
```
Prueba: `test_api_flujos.py::test_cu01_promocion_vigente_aplica_descuento`, `test_promocion_aplica_solo_vigente...`, `test_promocion_con_datos_invalidos_es_422` · `POST /promociones`
