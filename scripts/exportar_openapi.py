"""Exporta el contrato OpenAPI a docs/api/openapi.json (y .yaml si PyYAML está instalado)."""

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.api.aplicacion import crear_app  # noqa: E402
from src.api.contenedor import construir_contenedor  # noqa: E402
from src.infrastructure.config import Configuracion  # noqa: E402


def main() -> None:
    contenedor = construir_contenedor(Configuracion(database_url="sqlite://"))
    esquema = crear_app(contenedor).openapi()
    destino = RAIZ / "docs" / "api"
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "openapi.json").write_text(json.dumps(esquema, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OpenAPI exportado: {len(esquema['paths'])} rutas -> {destino / 'openapi.json'}")
    contenedor.motor.dispose()


if __name__ == "__main__":
    main()
