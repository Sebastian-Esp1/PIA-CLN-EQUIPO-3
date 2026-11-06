# Guía de defensa: preguntas probables y respuestas

**Demo (5 min):** `/docs` → crear pedido (MESA, PED-C001) → agregar PED-P011 (agotado, **409**) → agregar PED-P001 ×2 → autorizar → confirmar (**200**, inventario baja 2) → confirmar otra vez (**409 TRANSICION_INVALIDA**) → cancelar con rol MESERO (**403**) → cancelar con ENCARGADO (reintegra) → `GET /pedidos/{id}/historial`.
Cambiar rol: encabezados `X-Rol` y `X-Usuario` en Swagger (botón *Try it out*).

| Pregunta | Respuesta corta |
|---|---|
| ¿Por qué DDD y no Transaction Script? | Las reglas (RN-02..RN-13) se repiten entre casos de uso; en el dominio viven en un solo lugar y se prueban sin BD (ADR-01). |
| ¿Por qué Pedido es un solo Aggregate? | «Pedido completo» exige que todas sus líneas estén listas en una transacción (ADR-02). Dos estaciones simultáneas pueden chocar: control optimista con `version` → 409. |
| ¿Cómo evitan vender sin existencia? | Al confirmar se evalúa disponibilidad y se descuenta el inventario en la misma Unidad de Trabajo; si falla algo hay rollback (ADR-03, `test_..._hace_rollback`). |
| ¿Qué es una Specification y dónde la usan? | Regla componible con `&`, `|`, `~`. `puede_procesarse` (activo AND líneas AND autorizado) y `califica_beneficio` (preferente AND total ≥ 1500 AND NOT promoción). Explican qué hoja falló (`motivos_de_fallo`). |
| ¿Cómo funciona la máquina de estados? | `MaquinaDeEstados` con transiciones permitidas; `EstadoPedido` define si se puede modificar o cancelar. Saltos → 409 TRANSICION_INVALIDA. |
| ¿Qué eventos hay y cuándo se publican? | 15 eventos de dominio; se guardan en la bitácora dentro de la transacción y se publican tras el commit; `PedidoCerrado` alimenta el resumen de ventas (idempotente). |
| ¿Qué es CQRS básico aquí? | Comandos = dataclasses atendidas por servicios; consultas = clase `Consultas` con DTO sobre la misma BD, sin cargar Aggregates (ADR-04). |
| ¿Cómo adaptaron el paquete del docente? | El LEEME dice que es un modelo propuesto. Se importó a nuestro modelo y se documentó cada diferencia (`adaptacion_paquete_docente.md`). Oráculo calculado solo desde CSV: 120/120 y 20/20. |
| ¿Por qué cambiaron SP-06 (sin precios)? | El paquete trae precios MXN y la regla R2 compara con 1500; se modelan con `Decimal` (ADR-08). |
| ¿Cómo manejan la seguridad? | Roles vía `X-Rol`/`X-Usuario` y `X-API-Key` opcional; matriz de permisos en `AutorizadorPorRol`. Limitación: no es autenticación criptográfica; en producción se cambia por JWT detrás del mismo puerto. |
| ¿Qué cobertura tienen y cómo se mide? | 98.5 % de líneas y ramas con pytest-cov; el CI falla bajo 80 %. |
| ¿Qué defecto encontraron con las pruebas? | Choque de nombres entre un parámetro y un dato del evento al agregar modificaciones; corregido y cubierto. |
| ¿Qué pasa si dos usuarios editan el mismo pedido? | `UPDATE … WHERE version = ?`; el segundo recibe 409 CONFLICTO_DE_CONCURRENCIA (`test_concurrencia_optimista…`). |
| ¿Por qué Python y no C# como en la Unidad 3? | OpenAPI automático, despliegue gratuito y experiencia del equipo; se conservaron los nombres de la Unidad 3 (ADR-05). |
| ¿Qué falta o qué limitaciones hay? | los Gherkin originales son un escenario por historia y se ampliaron con casos de error; seguimiento del repartidor fuera de alcance (SP-07); ventas se actualizan en memoria (en producción, una cola). |
| ¿Cómo garantizan 12-Factor? | Configuración en variables de entorno (`config.py`, `.env.example`), logs a stdout, build y run separados (Dockerfile multi-etapa), sin secretos en el repo. |
| ¿Quién hizo qué? | Respuesta honesta según el reparto real del equipo (el trabajo del PIA fue individual si así ocurrió; decláralo). |
