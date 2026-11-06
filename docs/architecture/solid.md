# Evidencia de principios SOLID y patrones

| Principio / patrón | Dónde se ve | Evidencia |
|---|---|---|
| **S** Responsabilidad única | `Pedido` solo protege su ciclo de vida; `ConsumoDeIngredientes` solo el inventario; `AutorizadorPorRol` solo permisos | Archivos separados en `src/domain`, `src/infrastructure/seguridad.py` |
| **O** Abierto/cerrado | Nuevas condiciones de promoción = nueva `Specification`; nuevos eventos sin tocar el bus | `specifications.py`, `PublicadorEnMemoria.suscribir` |
| **L** Sustitución de Liskov | Cualquier `Specification` se compone con `&`, `\|`, `~`; el reloj y el autorizador se sustituyen por dobles | `RelojFijo` en `tests/conftest.py` |
| **I** Segregación de interfaces | Puertos pequeños: `IReloj`, `IAutorizador`, `IPublicadorDeEventos`, un repositorio por agregado, consultas separadas | `src/application/ports.py` |
| **D** Inversión de dependencias | `domain` no importa nada; `application` depende de puertos; `contenedor.py` conecta | `src/api/contenedor.py` |
| Specification | `puede_procesarse()` (AND), `califica_beneficio()` (AND/NOT), composición `&`,`\|`,`~` con `motivos_de_fallo` | `test_specifications.py` |
| State Machine | `MaquinaDeEstados` + `EstadoPedido` con matriz de modificación y cancelación | `test_value_objects_y_estados.py` |
| Domain Events | 15 eventos; bitácora en la misma transacción, publicación tras el commit | `test_eventos_se_guardan_en_bitacora…` |
| Repository + Unit of Work | Repositorios SQL, `UnidadDeTrabajoSql`, rollback atómico | `test_rollback_no_deja_cambios_parciales` |
| CQRS básico | Comandos (dataclasses) / `Consultas` con DTO | `src/application/commands.py`, `queries.py` |
| Concurrencia optimista | Columna `version` y `UPDATE … WHERE version = ?` | `test_concurrencia_optimista…` |
