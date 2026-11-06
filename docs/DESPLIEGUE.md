# Guía de entrega: GitHub, Docker y despliegue (lo que debes ejecutar tú)

## 1. Publicar el repositorio
```bash
unzip pia-sazon-urbano.zip && cd pia-sazon-urbano     # trae .git con 14 commits
git remote add origin https://github.com/<usuario>/<repo>.git
git push -u origin main
```
En GitHub: pestaña **Actions** → verificar que el pipeline queda en verde (captura para el reporte).
Opcional: Settings → Branches → proteger `main` exigiendo que pase el CI.

## 2. Probar Docker Compose en tu equipo (captura para el reporte)
```bash
docker compose up --build                       # http://localhost:8000/docs
docker compose --profile test run --rm tests    # Ruff + pytest + cobertura sobre PostgreSQL
docker compose down -v
```
Si el puerto 8000 está ocupado: `PORT=8080 docker compose up --build`.

## 3. Desplegar en Render
1. render.com → **New → Blueprint** → elegir el repositorio (lee `render.yaml`).
2. Crea el servicio web Docker y la base PostgreSQL; `DATABASE_URL` se conecta sola y `SEED_ON_START=true` carga los datos del docente.
3. Cuando esté **Live**, abrir `https://<servicio>.onrender.com/docs` y `/health`.
4. Pegar esa URL en `README.md` (fila «Despliegue»), en el reporte (portada y sección 1) y en la diapositiva 11. Hacer commit y push.
Nota: el plan gratuito duerme tras inactividad; abre la URL 1 minuto antes de la defensa.

Alternativa Railway: New Project → Deploy from GitHub → agregar plugin PostgreSQL → variables `DATABASE_URL` (referencia al plugin) y `SEED_ON_START=true`; usa el `Dockerfile` (target `prod`).

## 4. Capturas que faltan en el reporte (sección 7 y 11)
- Swagger UI desplegado (`/docs`) con POST confirmar expandido.
- Pipeline de GitHub Actions en verde.
- `docker compose` corriendo (app + db) y los tests en contenedor.
- Despliegue público.

## 5. Antes de la defensa
- [ ] README con URLs reales · [ ] CI verde · [ ] despliegue vivo y probado con el orden de la demo.
