# Sazón Urbano — Componentes de lógica de negocio (PIA)

API REST con lógica de negocio para pedidos de restaurante, construida con **DDD**, capas, Specification, máquina de estados,
Domain Events, CQRS básico, Unidad de Trabajo y concurrencia optimista. Implementa los casos de uso CU-01..CU-05 de las Unidades 2 y 3
y se valida con el paquete de datos del docente (120 casos + 20 transiciones).

| | |
|---|---|
| **Repositorio** | `https://github.com/<usuario>/<repositorio>`  ← _completar al publicar_ |
| **Despliegue (Swagger UI)** | `https://<servicio>.onrender.com/docs`  ← _completar tras desplegar_ |
| **OpenAPI** | `docs/api/openapi.json` y `/openapi.json` en el despliegue |
| **Equipo 3** | Jaime Sebastian Esparza Leyva (2097304) · Alan Joel Sánchez García (2082464) · Jorge Alejandro Jiménez González (2097849) |
| **Curso** | Componentes de lógica de negocios · UANL FIME · Docente: Miguel Ángel Gómez Marroquín |

## Estructura
```
docs/BRD.md                      requerimientos de negocio
docs/requirements/               US-01..US-15 con Gherkin
docs/architecture/               ADRs, trazabilidad, diagramas (PNG + Mermaid), BPMN, adaptación del paquete del docente
docs/api/openapi.json            contrato OpenAPI exportado
src/domain/                      Aggregates, Value Objects, Specifications, máquina de estados, Domain Services, eventos
src/application/                 servicios (comandos), consultas (DTO), puertos
src/infrastructure/              SQLAlchemy, Unidad de Trabajo, autorizador, importación CSV
src/api/                         FastAPI, esquemas, raíz de composición
tests/unit  tests/integration    268 pruebas (unitarias e integración)
data/                            paquete CSV del docente (datos ficticios)
Dockerfile · docker-compose.yml · .env.example · render.yaml · .github/workflows/ci.yml
```

## Ejecutar sin Docker
```bash
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                                       # opcional
SEED_ON_START=true uvicorn src.api.principal:app --reload  # carga los CSV al iniciar
```
Abrir <http://localhost:8000/docs>.

## Ejecutar con Docker Compose (DB + App + Tests)
```bash
docker compose up --build                       # PostgreSQL + API en http://localhost:8000/docs
docker compose --profile test run --rm tests    # Ruff + pytest con cobertura >= 80 % sobre PostgreSQL
docker compose down -v
```

## Pruebas y calidad
```bash
ruff check .
pytest --cov=src --cov-branch --cov-report=term-missing --cov-fail-under=80
pytest -m unit          # solo dominio
pytest -m integration   # repositorios, API y paquete del docente
python scripts/exportar_openapi.py              # regenera docs/api/openapi.json
```
Resultado actual: **267 pruebas en verde (1 más se omite sin PostgreSQL), cobertura 98.5 %** (mínimo exigido 80 %), Ruff sin observaciones.

## Uso rápido (demo)
Autenticación simulada por encabezados (ADR-09): `X-Usuario` y `X-Rol` (`MESERO`, `COCINERO`, `ENCARGADO`, `GERENTE`); `X-API-Key` solo si el servidor define `API_KEY`.
```bash
H='-H X-Usuario:demo -H X-Rol:GERENTE -H Content-Type:application/json'
curl -s $H -X POST localhost:8000/pedidos -d '{"canal":"MESA","cliente_id":"PED-C001"}'          # 201
curl -s $H -X POST localhost:8000/pedidos/<ID>/lineas -d '{"producto_id":"PED-P001","cantidad":2}'
curl -s $H -X POST localhost:8000/pedidos/<ID>/autorizar
curl -s $H -X POST localhost:8000/pedidos/<ID>/confirmar        # 200 y descuenta inventario
curl -s $H -X POST localhost:8000/pedidos/<ID>/cancelar -d '{"motivo":"el cliente se fue"}'
```

## Códigos HTTP
`200` acción correcta · `201` creación · `400` rango o rol inválido · `401` API key · `403` rol sin permiso · `404` no existe ·
`409` regla de negocio, estado o concurrencia · `422` datos inválidos. Los errores de negocio devuelven `{"codigo": ..., "mensaje": ...}`.

## Variables de entorno (12-Factor)
`DATABASE_URL`, `SEED_ON_START`, `APP_TIMEZONE`, `API_KEY`, `APP_ENV`, `DATA_DIR`, `PORT`. Ver `.env.example`. No hay secretos en el repositorio.

## CI/CD
`.github/workflows/ci.yml`: Ruff, pytest con cobertura ≥ 80 % en Python 3.11/3.12/3.13 con servicio PostgreSQL, exportación de OpenAPI y trabajo Docker (compose config, build, tests en contenedores y prueba de humo). El despliegue es automático desde `main` en Render (`render.yaml`).

## Trazabilidad
BRD → regla → historia → caso de uso → componente → prueba: `docs/architecture/trazabilidad.md`.

## Limitaciones declaradas
- BRD, historias y glosario de `docs/` están **reconstruidos** del informe de la Unidad 3; sustituir por los originales si se tienen.
- La autenticación por encabezados no es criptográfica (ADR-09).
- Seguimiento del repartidor fuera de alcance (SP-07).
