"""Punto de entrada: `uvicorn src.api.principal:app`."""

from src.api.aplicacion import crear_app

app = crear_app()
