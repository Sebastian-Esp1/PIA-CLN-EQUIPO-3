"""Script y estilos que muestran las respuestas de la API como tablas en la página /docs.

Swagger devuelve los datos en JSON (texto técnico). Este complemento los dibuja como tabla con
títulos en español y deja el JSON original disponible en el botón «Ver datos técnicos».
Si el script fallara, Swagger sigue mostrando el JSON normal.
"""

TABLA_AMIGABLE = r"""
<style>
.tabla-amigable { margin:8px 0 12px; font-family:'DM Sans',system-ui,sans-serif; }
.tabla-amigable table { border-collapse:collapse; width:100%; background:#fff; font-size:14px; }
.tabla-amigable th { background:#E8F1EB; color:#12301F; text-align:left; padding:8px 10px;
  border-bottom:2px solid #1B5E3A; white-space:nowrap; }
.tabla-amigable td { padding:8px 10px; border-bottom:1px solid #D3E2D7; vertical-align:top; color:#16241B; }
.tabla-amigable tr:nth-child(even) td { background:#F6F8F4; }
.tabla-amigable table table { font-size:13px; margin:2px 0; }
.tabla-amigable .ta-si, .tabla-amigable .ta-no { display:inline-block; padding:1px 10px; border-radius:10px;
  font-weight:600; font-size:13px; }
.tabla-amigable .ta-si { background:#DDF0E3; color:#1B5E3A; }
.tabla-amigable .ta-no { background:#FBE7D3; color:#8A4B0F; }
.tabla-amigable .ta-nulo { color:#8A978F; }
.tabla-amigable .ta-vacio { color:#4A5A50; font-style:italic; padding:8px 0; }
.tabla-amigable .ta-boton { margin-top:8px; background:#fff; color:#1B5E3A; border:1px solid #1B5E3A;
  border-radius:6px; padding:4px 12px; cursor:pointer; font-size:13px; }
.highlight-code.ta-oculto { display:none !important; }
</style>
<script>
(function () {
  var ETIQUETAS = {
    ingrediente_id:"Código", nombre:"Nombre", existencia:"Existencia", umbral:"Mínimo",
    es_critico:"¿Crítico?", pedido_id:"Pedido", canal:"Canal", cliente_id:"Cliente", estado:"Etapa",
    autorizado:"¿Autorizado?", promocion_id:"Promoción", beneficio_aplicado:"¿Con beneficio?",
    total:"Total ($)", descuento:"Descuento ($)", total_a_pagar:"A pagar ($)", lineas:"Productos",
    cancelacion:"Cancelación", linea_id:"Línea", producto_id:"Producto", cantidad:"Cantidad",
    precio_unitario:"Precio unitario ($)", subtotal:"Subtotal ($)", estacion:"Estación",
    estado_preparacion:"Preparación", modificaciones:"Indicaciones", tipo:"Tipo",
    descripcion:"Descripción", motivo:"Motivo", usuario:"Usuario", fecha:"Fecha", accion:"Acción",
    detalle:"Detalle", agregado:"¿Agregado?", pedido:"Pedido", pedido_listo:"¿Pedido listo?",
    producto:"Producto", disponible:"¿Disponible?", ingrediente:"Ingrediente",
    productos_afectados:"Productos afectados", fecha_cierre:"Fecha de cierre", total_productos:"Piezas",
    total_importe:"Importe ($)", existencia_esperada:"Esperada", existencia_registrada:"Registrada",
    diferencia:"Diferencia", agotado:"¿Agotado?", vigente:"¿Vigente?", clientes:"Clientes",
    productos:"Productos", pedidos:"Pedidos", codigo:"Código", mensaje:"Mensaje", estado_http:"Estado"
  };

  function etiqueta(k) {
    if (ETIQUETAS[k]) return ETIQUETAS[k];
    var t = String(k).replace(/_/g, " ");
    return t.charAt(0).toUpperCase() + t.slice(1);
  }
  function el(tag, clase, texto) {
    var e = document.createElement(tag);
    if (clase) e.className = clase;
    if (texto !== undefined) e.textContent = texto;
    return e;
  }
  function esObjeto(v) { return v !== null && typeof v === "object" && !Array.isArray(v); }

  function valor(v) {
    if (v === null || v === undefined) return el("span", "ta-nulo", "—");
    if (typeof v === "boolean") return el("span", v ? "ta-si" : "ta-no", v ? "Sí" : "No");
    if (typeof v === "string" && /^\d{4}-\d{2}-\d{2}T/.test(v)) {
      var d = new Date(v);
      return el("span", "", isNaN(d) ? v : d.toLocaleString("es-MX"));
    }
    if (Array.isArray(v)) {
      if (v.length === 0) return el("span", "ta-nulo", "Ninguno");
      if (v.every(function (x) { return !esObjeto(x) && !Array.isArray(x); })) {
        return el("span", "", v.join(", "));
      }
      return tabla(v);
    }
    if (esObjeto(v)) return ficha(v);
    return el("span", "", String(v));
  }

  function ficha(obj) {
    var t = el("table"), cuerpo = el("tbody");
    Object.keys(obj).forEach(function (k) {
      var fila = el("tr"), th = el("th", "", etiqueta(k)), td = el("td");
      th.style.borderBottom = "1px solid #D3E2D7";
      td.appendChild(valor(obj[k]));
      fila.appendChild(th); fila.appendChild(td); cuerpo.appendChild(fila);
    });
    t.appendChild(cuerpo);
    return t;
  }

  function tabla(filas) {
    var columnas = [];
    filas.forEach(function (f) {
      if (esObjeto(f)) Object.keys(f).forEach(function (k) { if (columnas.indexOf(k) < 0) columnas.push(k); });
    });
    var t = el("table"), cab = el("thead"), tr = el("tr");
    columnas.forEach(function (k) { tr.appendChild(el("th", "", etiqueta(k))); });
    cab.appendChild(tr); t.appendChild(cab);
    var cuerpo = el("tbody");
    filas.forEach(function (f) {
      var fila = el("tr");
      columnas.forEach(function (k) {
        var td = el("td");
        td.appendChild(valor(esObjeto(f) ? f[k] : f));
        fila.appendChild(td);
      });
      cuerpo.appendChild(fila);
    });
    t.appendChild(cuerpo);
    return t;
  }

  function construir(datos) {
    var cont = el("div", "tabla-amigable");
    if (Array.isArray(datos)) {
      if (datos.length === 0) cont.appendChild(el("div", "ta-vacio", "No hay registros para mostrar."));
      else if (datos.every(esObjeto)) cont.appendChild(tabla(datos));
      else cont.appendChild(valor(datos));
    } else if (esObjeto(datos)) {
      cont.appendChild(ficha(datos));
    } else {
      return null;
    }
    return cont;
  }

  function procesar() {
    var bloques = document.querySelectorAll(".live-responses-table .highlight-code");
    bloques.forEach(function (bloque) {
      var pre = bloque.querySelector("pre");
      if (!pre) return;
      var texto = pre.textContent;
      var previo = bloque.previousElementSibling;
      if (previo && previo.classList.contains("tabla-amigable") && previo.dataset.origen === texto) return;
      if (previo && previo.classList.contains("tabla-amigable")) previo.remove();
      var datos;
      try { datos = JSON.parse(texto); } catch (e) { return; }
      var cont = construir(datos);
      if (!cont) return;
      cont.dataset.origen = texto;
      var boton = el("button", "ta-boton", "Ver datos técnicos (JSON)");
      boton.type = "button";
      boton.addEventListener("click", function () {
        var oculto = bloque.classList.toggle("ta-oculto");
        boton.textContent = oculto ? "Ver datos técnicos (JSON)" : "Ocultar datos técnicos";
      });
      cont.appendChild(boton);
      bloque.classList.add("ta-oculto");
      bloque.parentNode.insertBefore(cont, bloque);
    });
  }

  var pendiente = false;
  new MutationObserver(function () {
    if (pendiente) return;
    pendiente = true;
    requestAnimationFrame(function () {
      pendiente = false;
      try { procesar(); } catch (e) { /* si falla, queda el JSON normal */ }
    });
  }).observe(document.documentElement, { childList: true, subtree: true, characterData: true });
})();
</script>
"""
