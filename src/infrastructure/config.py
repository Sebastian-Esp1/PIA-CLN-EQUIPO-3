"""Configuración por variables de entorno (12-Factor App): nada de secretos en el código."""

import os
from dataclasses import dataclass


def _bool(valor: str | None, defecto: bool) -> bool:
    if valor is None:
        return defecto
    return valor.strip().lower() in ("1", "true", "yes", "si", "sí")


@dataclass(frozen=True)
class Configuracion:
    database_url: str = "sqlite:///./sazon_urbano.db"
    seed_on_start: bool = False
    app_timezone: str = "America/Monterrey"
    api_key: str | None = None
    app_env: str = "development"
    data_dir: str = "data"

    @classmethod
    def desde_entorno(cls) -> "Configuracion":
        url = os.getenv("DATABASE_URL", cls.database_url)
        if url.startswith("postgres://"):  # formato que entregan algunas plataformas
            url = url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return cls(
            database_url=url,
            seed_on_start=_bool(os.getenv("SEED_ON_START"), False),
            app_timezone=os.getenv("APP_TIMEZONE", cls.app_timezone),
            api_key=os.getenv("API_KEY") or None,
            app_env=os.getenv("APP_ENV", cls.app_env),
            data_dir=os.getenv("DATA_DIR", cls.data_dir),
        )
