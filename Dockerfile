FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# --- imagen de pruebas: incluye herramientas de desarrollo ---
FROM base AS test
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt
COPY . .
CMD ["sh", "-c", "ruff check . && pytest --cov=src --cov-branch --cov-fail-under=80"]

# --- imagen de producción: solo lo necesario, usuario sin privilegios ---
FROM base AS prod
COPY src ./src
COPY data ./data
RUN useradd --create-home appuser
USER appuser
ENV PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD python -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/health')"
CMD ["sh", "-c", "uvicorn src.api.principal:app --host 0.0.0.0 --port ${PORT}"]
