"""Los diagramas UML/ER deben corresponder con el código implementado (trazabilidad diagrama ↔ código)."""

import importlib
import inspect
import pkgutil
import re
from pathlib import Path

import src.domain as dominio
from src.domain.state_machine import MAQUINA_PEDIDO, EstadoPedido
from src.infrastructure.modelos import Base

DIAGRAMAS = Path(__file__).resolve().parents[2] / "docs" / "architecture" / "diagrams"


def _clases_del_dominio():
    clases = {}
    for m in pkgutil.walk_packages(dominio.__path__, "src.domain."):
        modulo = importlib.import_module(m.name)
        for nombre, obj in inspect.getmembers(modulo, inspect.isclass):
            if obj.__module__ == modulo.__name__:
                clases[nombre] = obj
    return clases


def _leer(nombre):
    return (DIAGRAMAS / nombre).read_text(encoding="utf-8")


def test_clases_y_miembros_del_diagrama_de_dominio_existen_en_el_codigo():
    clases = _clases_del_dominio()
    bloques = re.findall(r"class (\w+) \{(.*?)\}\n", _leer("dominio.mmd") + "\n", re.S)
    assert len(bloques) >= 15
    faltantes = []
    for nombre, cuerpo in bloques:
        if nombre not in clases:
            faltantes.append(nombre)
            continue
        fuente = inspect.getsource(clases[nombre])
        for miembro in re.findall(r"\+([a-z_]+)", cuerpo):
            if not hasattr(clases[nombre], miembro) and not re.search(rf"\b{miembro}\b", fuente):
                faltantes.append(f"{nombre}.{miembro}")
    assert faltantes == []


def test_relaciones_de_composicion_del_diagrama_existen_en_el_codigo():
    clases = _clases_del_dominio()
    for padre, hijo in re.findall(r'(\w+) "[^"]*" \*-- "[^"]*" (\w+)', _leer("dominio.mmd")):
        # los hijos pueden guardarse como lista de objetos (campo) o por nombre de atributo
        fuente = inspect.getsource(clases[padre])
        asignaciones = {"LineaPedido": "lineas", "Modificacion": "modificaciones",
                        "RegistroDeCambio": "historial", "Cancelacion": "cancelacion",
                        "RequerimientoIngrediente": "receta", "MovimientoInventario": "movimientos"}
        assert hijo in fuente or asignaciones[hijo] in fuente, f"{padre} no contiene {hijo}"


def test_diagrama_de_estados_coincide_con_la_maquina_de_estados():
    dibujadas = set(re.findall(r"(\w+) --> (\w+)", _leer("estados.mmd")))
    reales = {(o.value, d.value) for o in EstadoPedido for d in MAQUINA_PEDIDO.destinos(o)}
    assert {t for t in dibujadas if "[*]" not in t} == reales


def test_diagrama_er_usa_exactamente_las_tablas_del_modelo():
    en_diagrama = set()
    for padre, hijo in re.findall(r"(\w+) [|}o]\S+ (\w+) :", _leer("er.mmd")):
        en_diagrama |= {padre, hijo}
    assert en_diagrama == set(Base.metadata.tables)


def test_relaciones_er_con_llave_foranea_son_reales_y_las_demas_estan_marcadas_como_logicas():
    texto = _leer("er.mmd")
    for padre, hijo, etiqueta in re.findall(r"(\w+) [|}o]\S+ (\w+) : (\w+)", texto):
        fks = {fk.column.table.name for fk in Base.metadata.tables[hijo].foreign_keys} | {
            fk.column.table.name for fk in Base.metadata.tables[padre].foreign_keys
        }
        tiene_fk = padre in fks or hijo in fks
        assert tiene_fk or etiqueta.endswith("_logica"), f"{padre}-{hijo} sin FK debe marcarse _logica"
        assert not (tiene_fk and etiqueta.endswith("_logica")), f"{padre}-{hijo} sí tiene FK"
