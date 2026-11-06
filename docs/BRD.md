# BRD — Sazón Urbano: sincronía entre pedidos, cocina, ventas e inventario

> **Procedencia.** BRD de la Unidad 2 (original en `requirements/originales_unidad2/BRD.pdf`), reorganizado en Markdown. Los supuestos SP-xx
> vienen del informe de la Unidad 3 y se marcan como tales.

## 1. Contexto
Sazón Urbano es un negocio de alimentos con servicio en mesa, para llevar y entrega a domicilio. Sus ingresos provienen de
alimentos, bebidas, paquetes y complementos. Los pedidos llegan por **mesa, teléfono, WhatsApp y domicilio** e incluyen productos,
cantidades y modificaciones especiales (quitar ingredientes, agregar extras). La cocina trabaja con cuatro **estaciones**:
parrilla, preparación fría, bebidas y empaque. El inventario se revisa principalmente **al final del día**.

## 2. Problema
Falta de sincronía entre pedidos, cocina, ventas e inventario: productos agotados que no se actualizan, órdenes incompletas,
diferencias entre ventas e inventario, modificaciones y cancelaciones difíciles de rastrear y productos registrados sin
disponibilidad real.

## 2.1 Oportunidad
Centralizar pedidos, disponibilidad, modificaciones, cancelaciones e inventario para reducir errores, mejorar la coordinación entre áreas,
dar visibilidad de la disponibilidad, reducir diferencias entre ventas e inventario, facilitar el seguimiento de pedidos y obtener
información confiable para decidir.

## 3. Objetivo
Contar con una lógica de negocio que haga cumplir las reglas del proceso de pedidos (disponibilidad, estados, trazabilidad,
inventario y promociones) de forma centralizada y verificable, expuesta mediante una API REST.

## 4. Stakeholders
| Rol | Interés |
|---|---|
| Gerente (stakeholder principal) | Ventas por periodo y comparativo ventas vs. inventario |
| Encargado | Existencias, ingredientes críticos, productos agotados, cancelaciones, promociones |
| Mesero / Caja | Registrar pedidos, modificaciones y confirmarlos |
| Cocina (cocinero) | Ver y preparar solo los productos de su estación |
| Repartidor | Entrega a domicilio (fuera del detalle de esta etapa, SP-07) |
| Cliente | Recibir el pedido completo y correcto |

## 5. Alcance
| Dentro | Fuera (esta etapa) |
|---|---|
| Registro y seguimiento de pedidos (mesa, teléfono, WhatsApp, domicilio) | Nómina |
| Productos, cantidades y modificaciones | Contabilidad completa |
| Disponibilidad de productos | Administración fiscal |
| Comunicación de pedidos a cocina y preparación por estaciones | Gestión integral de proveedores |
| Control de ingredientes y existencias | Recursos humanos y marketing |
| Cancelaciones, promociones y trazabilidad de cambios | Programas de socios |
| Consulta de ventas e inventario | |

## 6. Necesidades del negocio
| ID | Necesidad | Resuelto por (código) |
|---|---|---|
| N-01 | Control de pedidos | `src/domain/entities.py::Pedido`, `ServicioDePedidos` |
| N-02 | Comunicación con cocina | `Pedido.confirmar`, `ServicioDeCocina`, `GET /cocina/estaciones/{e}/ordenes` |
| N-03 | Control de disponibilidad | `DisponibilidadProductos`, `Producto.marcar_agotado` |
| N-04 | Control de inventario | `Ingrediente`, `ConsumoDeIngredientes`, `GET /reportes/comparativo-inventario` |
| N-05 | Trazabilidad y auditoría | `RegistroDeCambio`, `Cancelacion`, `GET /pedidos/{id}/historial` |
| N-06 | Gestión de excepciones | Errores de dominio con código, `ProductoRechazadoPorDisponibilidad`, cancelación con motivo |
| N-07 | Información para la gerencia | Lado de lectura (`Consultas`), `GET /reportes/ventas` |
| N-08 | Control de promociones | `Promocion`, `EvaluadorPromociones`, `POST /promociones` |

## 7. Reglas de negocio (RN-01..RN-15)
| ID | Regla |
|---|---|
| RN-01 | Todo pedido se registra con al menos un producto, cantidad mayor a cero y un canal de venta válido. |
| RN-02 | Un producto no disponible (agotado o con ingredientes insuficientes) no puede registrarse; se informa y se registra la incidencia. |
| RN-03 | Toda modificación o extra queda asociado a la línea correspondiente del pedido. |
| RN-04 | Cocina recibe el pedido confirmado con todos sus productos, cantidades y modificaciones. |
| RN-05 | Cada producto se prepara en su estación y cada estación ve únicamente sus productos. |
| RN-06 | Un producto preparado se marca como listo; el pedido está completo solo cuando todos sus productos están listos. |
| RN-07 | Solo un pedido activo puede cancelarse, por un usuario autorizado, con motivo, usuario, fecha y hora. |
| RN-08 | Las modificaciones y cancelaciones dependen del estado del pedido. |
| RN-09 | Toda modificación o cancelación conserva usuario, fecha y hora y es consultable en el historial. |
| RN-10 | La existencia de un ingrediente cambia por conteos y movimientos de entrada y salida. |
| RN-11 | Un ingrediente es crítico cuando su existencia llega al límite definido; se identifican los productos afectados. |
| RN-12 | La disponibilidad de un producto depende de las existencias de los ingredientes de su receta. |
| RN-13 | Una promoción se aplica solo si el pedido está dentro del horario y cumple sus condiciones. |
| RN-14 | Una venta se registra a partir de un pedido procesado y cerrado. |
| RN-15 | El comparativo muestra diferencias entre inventario esperado y registrado. |

## 8. Supuestos (SP) y su estado en el PIA
| ID | Supuesto | Estado en el PIA |
|---|---|---|
| SP-01 | Estados: EnRegistro, Confirmado, EnPreparación, Listo, Cerrado, Cancelado | Implementado (`EstadoPedido`) |
| SP-02 | Modificar en EnRegistro/Confirmado; cancelar en EnRegistro/Confirmado/EnPreparación | Implementado y probado |
| SP-03 | Umbral crítico por ingrediente (existencia ≤ umbral) | Implementado (`UmbralCritico`) |
| SP-04 | Consumo teórico al confirmar, misma transacción | Implementado (ADR-03) |
| SP-05 | Cancelan Encargado y Gerente | Implementado; el resto recibe 403 |
| **SP-06** | *No se modelan precios* | **Revisado:** el paquete del docente trae precios en MXN → se modelan con `Decimal` (ver `docs/architecture/adaptacion_paquete_docente.md`) |
| SP-07 | Seguimiento de repartidor solo hasta Listo/Cerrado | Sin cambio |
| SP-08 | Cancelar en Confirmado reintegra ingredientes; en EnPreparación no (merma) | Implementado y probado |
| SP-09 | Autenticación y roles en infraestructura | Implementado con encabezados `X-Usuario`/`X-Rol` y `X-API-Key` opcional |

## 9. Restricciones (BRD original)
- La operación debe seguir atendiendo diferentes canales de pedido.
- El sistema debe adaptarse a los procesos actuales de Sazón Urbano.
- Los empleados deben poder usarlo sin conocimientos técnicos avanzados.
- La información debe mantenerse consistente entre pedidos, ventas e inventario.
- Las operaciones de cocina no deben interrumpirse por procesos administrativos.
- El control de inventario depende de que las existencias registradas sean correctas.
- Las promociones pueden tener condiciones y horarios específicos que deben respetarse.
- Las modificaciones y cancelaciones deben considerar el estado del pedido.
- (PIA) Los datos del paquete del docente son ficticios (MXN, ISO 8601).

## 10. Criterios de éxito (BRD original) y cómo se verifican
| Criterio | Resultado esperado | Verificación en el PIA |
|---|---|---|
| Exactitud de pedidos | Menos errores por información incompleta o modificaciones no comunicadas | Modificaciones por línea visibles en cocina (US-02, US-06) |
| Disponibilidad | Menos pedidos con productos que luego resultan agotados | Rechazo 409 y confirmación con descuento transaccional (US-04) |
| Inventario | Menos diferencias entre ventas y existencias | Consumo al confirmar, reintegro al cancelar, comparativo (US-14) |
| Trazabilidad | Identificar modificaciones y cancelaciones | Historial inmutable con usuario, fecha y motivo (US-11, US-12) |
| Operación de cocina | Órdenes claras y completas por estación | Consulta por estación (US-07) |
| Gestión de pedidos | Conocer el estado del pedido de registro a entrega | Máquina de estados y `GET /pedidos/{id}` |
| Promociones | Aplicarlas según sus condiciones | `Promocion` + `EvaluadorPromociones` (US-15) |
| Toma de decisiones | Información confiable para el gerente | Reportes de ventas y comparativo (US-13, US-14) |
