"""Casos de uso CU-01..CU-05 de punta a punta a través de la API REST y códigos HTTP del contrato."""

import pytest

pytestmark = pytest.mark.integration

MESERO = {"X-Usuario": "mesero1", "X-Rol": "MESERO"}
COCINERO = {"X-Usuario": "cocinero1", "X-Rol": "COCINERO"}
ENCARGADO = {"X-Usuario": "encargado1", "X-Rol": "ENCARGADO"}
GERENTE = {"X-Usuario": "gerente1", "X-Rol": "GERENTE"}
CLIENTE, PREFERENTE, INACTIVO = "PED-C001", "PED-C005", None
PRODUCTO, DESHABILITADO = "PED-P001", "PED-P011"


def nuevo_pedido(api, cliente=CLIENTE, canal="MESA", headers=MESERO):
    r = api.post("/pedidos", json={"canal": canal, "cliente_id": cliente}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["pedido_id"]


def agregar(api, pid, producto=PRODUCTO, cantidad=1, headers=MESERO):
    return api.post(f"/pedidos/{pid}/lineas", json={"producto_id": producto, "cantidad": cantidad}, headers=headers)


def existencia(api, producto=PRODUCTO):
    datos = {i["ingrediente_id"]: i for i in api.get("/inventario/ingredientes").json()}
    return float(datos[f"ING-{producto}"]["existencia"])


def listo_para_confirmar(api, producto=PRODUCTO, cantidad=1, cliente=CLIENTE):
    pid = nuevo_pedido(api, cliente)
    assert agregar(api, pid, producto, cantidad).status_code == 201
    assert api.post(f"/pedidos/{pid}/autorizar", headers=MESERO).status_code == 200
    return pid


# --- CU-01 -------------------------------------------------------------------------------------
def test_health_y_documentacion_openapi(api):
    assert api.get("/health").json()["estado"] == "ok"
    esquema = api.get("/openapi.json").json()
    assert esquema["info"]["title"].startswith("Sazón Urbano")
    assert "/pedidos/{pedido_id}/confirmar" in esquema["paths"]
    pagina = api.get("/docs")
    assert pagina.status_code == 200 and "Sazón Urbano" in pagina.text and "swagger-ui" in pagina.text
    assert [t["name"] for t in esquema["tags"]][0] == "Pedidos"
    inicio = api.get("/", follow_redirects=False)
    assert inicio.status_code in (302, 307) and inicio.headers["location"] == "/docs"


def test_cu01_registrar_y_confirmar_descuenta_inventario_en_una_transaccion(api):
    antes = existencia(api)
    pid = listo_para_confirmar(api, cantidad=3)
    r = api.post(f"/pedidos/{pid}/confirmar", headers=MESERO)
    assert r.status_code == 200 and r.json()["estado"] == "CONFIRMADO"
    assert existencia(api) == antes - 3
    acciones = [h["accion"] for h in api.get(f"/pedidos/{pid}/historial").json()]
    assert acciones[0] == "Pedido iniciado" and acciones[-1] == "Pedido confirmado"


def test_cu01_confirmar_sin_autorizacion_o_sin_lineas_o_cliente_inactivo_es_409(api):
    sin_autorizar = nuevo_pedido(api)
    agregar(api, sin_autorizar)
    r = api.post(f"/pedidos/{sin_autorizar}/confirmar", headers=MESERO)
    assert r.status_code == 409 and r.json()["codigo"] == "PEDIDO_NO_PROCESABLE"
    vacio = nuevo_pedido(api)
    api.post(f"/pedidos/{vacio}/autorizar", headers=MESERO)
    assert api.post(f"/pedidos/{vacio}/confirmar", headers=MESERO).status_code == 409
    inactivos = [c for c in (f"PED-C{n:03d}" for n in range(1, 41))]
    pid = None
    for candidato in inactivos:  # busca un cliente inactivo del paquete
        r = api.post("/pedidos", json={"canal": "MESA", "cliente_id": candidato}, headers=MESERO)
        pid = r.json()["pedido_id"]
        agregar(api, pid)
        api.post(f"/pedidos/{pid}/autorizar", headers=MESERO)
        if api.post(f"/pedidos/{pid}/confirmar", headers=MESERO).status_code == 409:
            assert "activo" in api.post(f"/pedidos/{pid}/confirmar", headers=MESERO).json()["mensaje"]
            break
    else:
        pytest.fail("el paquete debería incluir al menos un cliente inactivo")


def test_cu01_confirmacion_con_existencia_insuficiente_hace_rollback(api):
    pid = listo_para_confirmar(api, cantidad=1)
    api.post("/inventario/ingredientes/ING-PED-P001/conteo", json={"cantidad_contada": "0"}, headers=ENCARGADO)
    antes = existencia(api)
    r = api.post(f"/pedidos/{pid}/confirmar", headers=MESERO)
    assert r.status_code == 409 and r.json()["codigo"] in {"PRODUCTO_NO_DISPONIBLE", "EXISTENCIA_INSUFICIENTE"}
    assert api.get(f"/pedidos/{pid}").json()["estado"] == "EN_REGISTRO"
    assert existencia(api) == antes


def test_cu01_modificaciones_extras_por_linea(api):
    pid = nuevo_pedido(api)
    agregar(api, pid)
    r = api.post(f"/pedidos/{pid}/lineas/1/modificaciones", json={"tipo": "QUITAR", "descripcion": "sin cebolla"}, headers=MESERO)
    assert r.status_code == 201 and r.json()["lineas"][0]["modificaciones"][0]["descripcion"] == "sin cebolla"
    mal = api.post(f"/pedidos/{pid}/lineas/1/modificaciones", json={"tipo": "BORRAR", "descripcion": "x"}, headers=MESERO)
    assert mal.status_code == 422 and mal.json()["codigo"] == "DATO_INVALIDO"


def test_cu01_promocion_vigente_aplica_descuento(api):
    r = api.post(
        "/promociones",
        json={"promocion_id": "PROMO-T", "nombre": "Siempre", "hora_inicio": "00:00", "hora_fin": "23:59",
              "total_minimo": "100", "descuento_pct": "10"},
        headers=ENCARGADO,
    )
    assert r.status_code == 201
    pid = listo_para_confirmar(api, cantidad=2)  # 2 x 290
    r = api.post(f"/pedidos/{pid}/confirmar", headers=MESERO).json()
    assert r["promocion_id"] == "PROMO-T" and r["descuento"] == "58.00" and r["total_a_pagar"] == "522.00"


def test_beneficio_preferente_con_total_minimo(api):
    api.post("/inventario/ingredientes/ING-PED-P001/movimientos", json={"tipo": "ENTRADA", "cantidad": "100"}, headers=ENCARGADO)
    pid = listo_para_confirmar(api, cantidad=6, cliente=PREFERENTE)  # 6 x 290 = 1740
    assert api.post(f"/pedidos/{pid}/confirmar", headers=MESERO).json()["beneficio_aplicado"] is True


# --- CU-02 -------------------------------------------------------------------------------------
def test_cu02_producto_agotado_se_rechaza_y_deja_incidencia(api):
    pid = nuevo_pedido(api)
    r = agregar(api, pid, DESHABILITADO)
    assert r.status_code == 409 and r.json()["codigo"] == "PRODUCTO_NO_DISPONIBLE"
    assert api.get(f"/pedidos/{pid}").json()["lineas"] == []
    historial = api.get(f"/pedidos/{pid}/historial").json()
    assert historial[-1]["accion"] == "Producto rechazado por disponibilidad"


def test_cu02_agotar_y_reactivar_producto(api):
    assert api.post(f"/productos/{PRODUCTO}/agotar", headers=ENCARGADO).json()["agotado"] is True
    pid = nuevo_pedido(api)
    assert agregar(api, pid).status_code == 409
    assert api.post(f"/productos/{PRODUCTO}/reactivar", headers=ENCARGADO).json()["agotado"] is False
    assert agregar(api, pid).status_code == 201
    disponibilidad = {d["producto_id"]: d for d in api.get("/productos/disponibilidad").json()}
    assert disponibilidad[PRODUCTO]["disponible"] and not disponibilidad[DESHABILITADO]["disponible"]


def test_cantidad_mayor_a_la_existencia_no_se_agrega(api):
    pid = nuevo_pedido(api)
    assert agregar(api, pid, PRODUCTO, 999).status_code == 409


# --- CU-03 -------------------------------------------------------------------------------------
def test_cu03_cocina_prepara_por_estacion_y_pedido_queda_listo(api):
    pid = nuevo_pedido(api)
    agregar(api, pid, "PED-P001")  # hamburguesa
    agregar(api, pid, "PED-P002")  # ensalada
    api.post(f"/pedidos/{pid}/autorizar", headers=MESERO)
    api.post(f"/pedidos/{pid}/confirmar", headers=MESERO)
    pendientes = api.get("/cocina/estaciones/PARRILLA/ordenes").json()
    assert any(o["pedido_id"] == pid for o in pendientes)
    base = f"/cocina/pedidos/{pid}/lineas"
    assert api.post(f"{base}/1/iniciar", headers=COCINERO).status_code == 200
    r = api.post(f"{base}/1/listo", headers=COCINERO).json()
    assert r["pedido_listo"] is False
    api.post(f"{base}/2/iniciar", headers=COCINERO)
    r = api.post(f"{base}/2/listo", headers=COCINERO).json()
    assert r["pedido_listo"] is True and r["pedido"]["estado"] == "LISTO"
    assert api.post(f"/pedidos/{pid}/cerrar", headers=MESERO).json()["estado"] == "CERRADO"


def test_estacion_invalida_es_422(api):
    assert api.get("/cocina/estaciones/PATIO/ordenes").status_code == 422


# --- CU-04 -------------------------------------------------------------------------------------
def test_cu04_cancelar_confirmado_reintegra_existencias_y_exige_rol(api):
    antes = existencia(api)
    pid = listo_para_confirmar(api, cantidad=2)
    api.post(f"/pedidos/{pid}/confirmar", headers=MESERO)
    assert existencia(api) == antes - 2
    assert api.post(f"/pedidos/{pid}/cancelar", json={"motivo": "x"}, headers=MESERO).status_code == 403
    r = api.post(f"/pedidos/{pid}/cancelar", json={"motivo": "cliente se fue"}, headers=ENCARGADO)
    assert r.status_code == 200 and r.json()["estado"] == "CANCELADO"
    assert existencia(api) == antes
    assert r.json()["cancelacion"]["usuario"] == "encargado1"


def test_cu04_cancelar_sin_motivo_listo_o_inexistente(api):
    pid = nuevo_pedido(api)
    r = api.post(f"/pedidos/{pid}/cancelar", json={"motivo": "  "}, headers=ENCARGADO)
    assert r.status_code == 422 and r.json()["codigo"] == "MOTIVO_REQUERIDO"
    assert api.post("/pedidos/NOEXISTE/cancelar", json={"motivo": "x"}, headers=ENCARGADO).status_code == 404
    assert api.post(f"/pedidos/{pid}/cancelar", json={"motivo": "ok"}, headers=ENCARGADO).status_code == 200
    r = api.post(f"/pedidos/{pid}/cancelar", json={"motivo": "otra vez"}, headers=ENCARGADO)
    assert r.status_code == 409 and r.json()["codigo"] == "CANCELACION_NO_PERMITIDA"


def test_cancelacion_en_registro_no_toca_inventario(api):
    antes = existencia(api)
    pid = listo_para_confirmar(api)
    api.post(f"/pedidos/{pid}/cancelar", json={"motivo": "x"}, headers=ENCARGADO)
    assert existencia(api) == antes


# --- CU-05 e inventario ------------------------------------------------------------------------
def test_cu05_movimientos_conteo_umbral_y_criticos(api):
    base = "/inventario/ingredientes/ING-PED-P002"
    r = api.post(f"{base}/movimientos", json={"tipo": "ENTRADA", "cantidad": "4"}, headers=ENCARGADO)
    assert r.status_code == 200
    inicial = float(r.json()["existencia"])
    r = api.post(f"{base}/movimientos", json={"tipo": "SALIDA", "cantidad": "1"}, headers=ENCARGADO)
    assert float(r.json()["existencia"]) == inicial - 1
    assert api.post(f"{base}/movimientos", json={"tipo": "SALIDA", "cantidad": "9999"}, headers=ENCARGADO).status_code == 409
    assert api.post(f"{base}/movimientos", json={"tipo": "OTRO", "cantidad": "1"}, headers=ENCARGADO).status_code == 422
    conteo = api.post(f"{base}/conteo", json={"cantidad_contada": "2"}, headers=ENCARGADO)
    assert float(conteo.json()["existencia"]) == 2
    assert api.put(f"{base}/umbral", json={"umbral": "50"}, headers=ENCARGADO).json()["es_critico"] is True
    criticos = api.get("/inventario/criticos").json()
    fila = next(c for c in criticos if c["ingrediente_id"] == "ING-PED-P002")
    assert "Ensalada 02" in fila["productos_afectados"]
    assert api.post("/inventario/ingredientes/NOEXISTE/movimientos", json={"tipo": "ENTRADA", "cantidad": "1"}, headers=ENCARGADO).status_code == 404


# --- US-13 / US-14 ------------------------------------------------------------------------------
def test_reportes_de_ventas_y_comparativo(api, reloj):
    pid = listo_para_confirmar(api, cantidad=2)
    api.post(f"/pedidos/{pid}/confirmar", headers=MESERO)
    base = f"/cocina/pedidos/{pid}/lineas/1"
    api.post(f"{base}/iniciar", headers=COCINERO)
    api.post(f"{base}/listo", headers=COCINERO)
    api.post(f"/pedidos/{pid}/cerrar", headers=MESERO)
    rango = {"desde": "2026-01-01T00:00:00", "hasta": "2026-12-31T23:59:59"}
    ventas = api.get("/reportes/ventas", params=rango, headers=GERENTE).json()
    venta = next(v for v in ventas if v["pedido_id"] == pid)
    assert venta["total_productos"] == 2 and venta["total_importe"] == "580.00"
    comparativo = api.get("/reportes/comparativo-inventario", params=rango, headers=GERENTE)
    assert comparativo.status_code == 200 and comparativo.json()
    assert api.get("/reportes/ventas", params=rango, headers=MESERO).status_code == 403
    invertido = {"desde": "2026-12-31T00:00:00", "hasta": "2026-01-01T00:00:00"}
    assert api.get("/reportes/ventas", params=invertido, headers=GERENTE).status_code == 400
    assert api.get("/reportes/comparativo-inventario", params=invertido, headers=GERENTE).status_code == 400
    assert api.get("/reportes/comparativo-inventario", params=rango, headers=MESERO).status_code == 403


# --- Contrato HTTP, validación y roles --------------------------------------------------------
def test_codigos_http_del_contrato(api):
    assert api.post("/pedidos", json={"canal": "MESA", "cliente_id": CLIENTE}, headers=MESERO).status_code == 201  # 201
    assert api.get("/pedidos").status_code == 200  # 200
    assert api.get("/pedidos/NOEXISTE").status_code == 404  # 404
    assert api.get("/pedidos/NOEXISTE/historial").status_code == 404
    assert api.post("/pedidos", json={"canal": "MESA"}, headers=MESERO).status_code == 422  # esquema inválido
    assert api.post("/pedidos", json={"canal": "MOSTRADOR", "cliente_id": CLIENTE}, headers=MESERO).status_code == 422
    assert api.post("/pedidos", json={"canal": "MESA", "cliente_id": "NO"}, headers=MESERO).status_code == 404
    assert api.post("/pedidos", json={"canal": "MESA", "cliente_id": CLIENTE}, headers={"X-Rol": "INTRUSO"}).status_code == 400
    assert api.post("/pedidos", json={"canal": "MESA", "cliente_id": CLIENTE}, headers=COCINERO).status_code == 403


@pytest.mark.parametrize("cantidad", [0, -2])
def test_cantidades_invalidas_son_422(api, cantidad):
    pid = nuevo_pedido(api)
    r = agregar(api, pid, PRODUCTO, cantidad)
    assert r.status_code == 422 and r.json()["codigo"] == "DATO_INVALIDO"


def test_producto_inexistente_es_404(api):
    assert agregar(api, nuevo_pedido(api), "NO-EXISTE").status_code == 404


def test_listar_pedidos_filtra_por_estado(api):
    pid = nuevo_pedido(api)
    en_registro = api.get("/pedidos", params={"estado": "EN_REGISTRO", "limite": 500}).json()
    assert pid in {p["pedido_id"] for p in en_registro}
    assert all(p["estado"] == "EN_REGISTRO" for p in en_registro)
    assert api.get("/pedidos", params={"limite": 0}).status_code == 422


def test_matriz_de_roles(api):
    assert api.post(f"/productos/{PRODUCTO}/agotar", headers=MESERO).status_code == 403
    assert api.post("/inventario/ingredientes/ING-PED-P001/movimientos", json={"tipo": "ENTRADA", "cantidad": "1"}, headers=COCINERO).status_code == 403
    assert api.post("/promociones", json={"promocion_id": "X", "nombre": "x", "hora_inicio": "10:00", "hora_fin": "11:00"}, headers=MESERO).status_code == 403
    assert api.post("/admin/importar-csv", headers=MESERO).status_code == 403
    r = api.post("/admin/importar-csv", headers=GERENTE)
    assert r.status_code == 200 and r.json()["pedidos"] == 0  # idempotente: ya estaba cargado


def test_promocion_con_datos_invalidos_es_422(api):
    base = {"promocion_id": "P1", "nombre": "x", "hora_inicio": "19:00", "hora_fin": "16:00"}
    assert api.post("/promociones", json=base, headers=ENCARGADO).status_code == 422
    assert api.post("/promociones", json={**base, "hora_inicio": "xx"}, headers=ENCARGADO).status_code == 422


def test_api_key_opcional_protege_la_api(datos):
    contenedor = datos
    from dataclasses import replace

    from fastapi.testclient import TestClient

    from src.api.aplicacion import crear_app

    contenedor.configuracion = replace(contenedor.configuracion, api_key="secreto")
    with TestClient(crear_app(contenedor)) as c:
        cuerpo = {"canal": "MESA", "cliente_id": CLIENTE}
        assert c.post("/pedidos", json=cuerpo, headers=MESERO).status_code == 401
        assert c.post("/pedidos", json=cuerpo, headers={**MESERO, "X-API-Key": "secreto"}).status_code == 201


def test_documentacion_en_lenguaje_de_negocio(api):
    """Swagger muestra títulos claros, descripciones y ejemplos realistas, no 'string'."""
    esquema = api.get("/openapi.json").json()
    op = esquema["paths"]["/inventario/ingredientes"]["get"]
    assert op["summary"] == "Ver cuánto hay de cada ingrediente"
    assert op["responses"]["200"]["description"] == "Existencias de ingredientes"
    ejemplo = esquema["components"]["schemas"]["IngredienteOut"]["examples"][0]
    assert ejemplo["nombre"] != "string" and ejemplo["es_critico"] is False
    sin_titulo = [
        f"{m} {ruta}"
        for ruta, ops in esquema["paths"].items()
        for m, o in ops.items()
        if not o.get("description") and ruta != "/health"
    ]
    assert sin_titulo == []


def test_docs_incluye_tabla_amigable_para_respuestas(api):
    """La página /docs trae el complemento que muestra las respuestas como tabla (Sí/No)."""
    html = api.get("/docs").text
    assert "tabla-amigable" in html and "Ver datos técnicos" in html
    assert '"¿Crítico?"' in html
