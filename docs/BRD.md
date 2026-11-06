# BRD — Sazón Urbano: sincronía entre pedidos, cocina, ventas e inventario

> **Procedencia.** Este documento reúne el BRD de la Unidad 2 tal como lo recoge el *Informe de arquitectura* de la Unidad 3
> (empresa, problema, alcance, necesidades N-01..N-08, restricciones y supuestos). Si el equipo conserva el BRD original en
> Word, ese archivo manda y esta versión debe sustituirse o contrastarse con él. Lo que no estaba definido en la Unidad 2
> aparece marcado como **supuesto (SP-xx)**.

## 1. Contexto
Sazón Urbano es un negocio de alimentos con servicio en mesa, para llevar y entrega a domicilio. Sus ingresos provienen de
alimentos, bebidas, paquetes y complementos. Los pedidos llegan por **mesa, teléfono, WhatsApp y domicilio** e incluyen productos,
cantidades y modificaciones especiales (quitar ingredientes, agregar extras). La cocina trabaja con cuatro **estaciones**:
parrilla, preparación fría, bebidas y empaque. El inventario se revisa principalmente **al final del día**.

## 2. Problema
Falta de sincronía entre pedidos, cocina, ventas e inventario: productos agotados que no se actualizan, órdenes incompletas,
diferencias entre ventas e inventario, modificaciones y cancelaciones difíciles de rastrear y productos registrados sin
disponibilidad real.

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

## 9. Restricciones
- Las modificaciones y cancelaciones deben considerar el estado del pedido.
- Las promociones solo aplican dentro de su horario y condiciones.
- Los datos del paquete del docente son ficticios (MXN, ISO 8601).

## 10. Criterios de éxito
1. No se confirma un pedido con productos no disponibles ni con existencia insuficiente.
2. Todo cambio y cancelación deja usuario, fecha, hora y motivo.
3. El inventario esperado se actualiza al confirmar y se reintegra al cancelar según SP-08.
4. Gerencia puede consultar ventas por periodo y el comparativo contra inventario.
5. El servicio corre en un despliegue público con documentación OpenAPI, pruebas con cobertura ≥ 80 % y CI/CD activo.
