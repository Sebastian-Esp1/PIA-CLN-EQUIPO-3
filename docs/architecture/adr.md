# Architecture Decision Records

Estados: las ADR-01..04 vienen de la Unidad 3 (estaban en *Propuesta*) y aquí pasan a **Aceptada** porque quedaron implementadas y
probadas. Las ADR-05..09 son nuevas del PIA.

## ADR-01 Domain Model como patrón principal — Aceptada
**Contexto.** Las reglas de disponibilidad, estados, trazabilidad y promociones (RN-02..RN-13) deben cumplirse siempre.
**Alternativas.** Transaction Script (duplica reglas); Table Module (reglas sin dueño); Domain Model + consultas aparte.
**Decisión.** Domain Model para todo lo que cambia estado; las consultas van por un lado de lectura.
**Consecuencias.** Reglas en un solo lugar y trazabilidad por construcción; más código. **Evidencia:** `src/domain/`, 90 pruebas unitarias.

## ADR-02 Pedido como un único Aggregate — Aceptada
**Decisión.** Líneas, estado de preparación e historial viven dentro de `Pedido`, de modo que «pedido completo» (RN-06) se garantiza en una transacción.
**Consecuencias.** Dos estaciones simultáneas pueden chocar por versión; se resuelve con concurrencia optimista (columna `version`, error 409 `CONFLICTO_DE_CONCURRENCIA`). **Evidencia:** `test_concurrencia_optimista_rechaza_la_segunda_escritura_vieja`.

## ADR-03 Consumo de ingredientes al confirmar, en una sola transacción — Aceptada
**Decisión.** `confirmar_pedido` cambia el pedido y los ingredientes de la receta en una Unidad de Trabajo; si algo falla hay rollback total.
**Consecuencias.** Rompe conscientemente «un Aggregate por transacción»; ingredientes muy usados pueden reintentar. **Evidencia:** `test_cu01_confirmacion_con_existencia_insuficiente_hace_rollback`, `test_rollback_no_deja_cambios_parciales`.

## ADR-04 CQRS básico sin bases separadas — Aceptada
**Decisión.** Comandos = dataclasses atendidas por métodos de servicio que usan el dominio; consultas = clase `Consultas` que devuelve DTO leyendo directo de la base. `VentaResumen` se alimenta del evento `PedidoCerrado` **después del commit**.
**Riesgo.** Si el suscriptor falla, el resumen queda desactualizado; el actualizador es idempotente y puede reprocesarse. **Evidencia:** `test_la_venta_se_registra_una_sola_vez`.

## ADR-05 Python 3.11+, FastAPI y SQLAlchemy 2 en lugar del esqueleto C# de la Unidad 3 — Aceptada
**Contexto.** El PIA exige API REST con OpenAPI, Docker Compose, CI/CD y despliegue; el curso permite la tecnología del equipo. El *Código Base* de la Unidad 3 estaba en C#, pero solo era ilustrativo.
**Decisión.** Python + FastAPI (OpenAPI automático con Swagger UI), Pydantic v2 para contratos, SQLAlchemy 2 para persistencia, pytest/Ruff para calidad.
**Alternativas.** ASP.NET Core (coherente con el esqueleto, pero sin experiencia de despliegue gratuito del equipo); Django (más pesado, ORM acoplado al dominio).
**Consecuencias.** Los nombres de la Unidad 3 se conservan (`Pedido`, `ServicioDePedidos`, `IUnitOfWork`...) con convenciones Python (`snake_case`).

## ADR-06 Capas con inversión de dependencias y raíz de composición — Aceptada
**Decisión.** `domain` no importa nada de afuera; `application` depende de puertos (`IUnitOfWork`, `IAutorizador`, `IReloj`, repositorios, consultas); `infrastructure` los implementa; `api` solo traduce HTTP y arma todo en `contenedor.py`.
**Consecuencias.** El dominio se prueba sin base de datos ni HTTP y el reloj se sustituye para pruebas deterministas.

## ADR-07 Adaptación del paquete de datos del docente al modelo propio — Aceptada
**Contexto.** El paquete trae actores/catálogo/operaciones planos y reglas ilustrativas; el PIA exige derivar del BRD propio.
**Decisión.** Se importa el CSV hacia el modelo del equipo y se documentan las diferencias (ver `adaptacion_paquete_docente.md`). Las reglas R1 y R2 del docente se implementan como **Specifications** componibles, **separadas** del flujo propio de estados; los oráculos de prueba se calculan solo desde el CSV.
**Consecuencias.** Se conservan los requerimientos propios y el paquete funciona como conjunto de pruebas independiente.

## ADR-08 Precios y totales con `Decimal` (revisión de SP-06) — Aceptada
**Contexto.** La Unidad 3 supuso que no había precios; el paquete del docente los trae (MXN) y la regla R2 compara contra 1500.
**Decisión.** `LineaPedido` guarda el precio vigente al momento de agregar; todo cálculo usa `Decimal` redondeado a centavos; la API devuelve importes como cadena para evitar errores de coma flotante.

## ADR-09 Autorización por roles con encabezados y API key opcional — Aceptada
**Contexto.** SP-09 dice que el dominio no resuelve seguridad. La entrega necesita demostrar roles sin un proveedor de identidad.
**Decisión.** `X-Usuario` y `X-Rol` (MESERO, COCINERO, ENCARGADO, GERENTE) llegan a un `Usuario`; `AutorizadorPorRol` aplica la matriz de permisos; `API_KEY` opcional protege el despliegue con `X-API-Key`.
**Consecuencias.** Suficiente para la defensa; en producción real se sustituiría por JWT/OIDC detrás del mismo puerto `IAutorizador`.
**Limitación declarada.** Los encabezados no están autenticados criptográficamente.
