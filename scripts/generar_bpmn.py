"""Genera docs/architecture/bpmn_to_be.bpmn (BPMN 2.0 con diagrama DI) del proceso TO-BE del pedido."""

from pathlib import Path

DESTINO = Path(__file__).resolve().parent.parent / "docs" / "architecture" / "bpmn_to_be.bpmn"
LANES = ["Mesero / Caja", "Sistema (API)", "Cocina", "Encargado"]
LH, X0, W, H = 130, 170, 130, 60
# id, tipo, nombre, carril, columna
NODOS = [
    ("ini", "startEvent", "Llega pedido", 0, 0),
    ("t1", "task", "Iniciar pedido (canal, cliente)", 0, 1),
    ("t2", "task", "Agregar producto y modificaciones", 0, 2),
    ("g1", "exclusiveGateway", "¿Producto disponible?", 1, 3),
    ("t3", "task", "Registrar incidencia y avisar", 1, 4),
    ("t4", "task", "Autorizar y confirmar pedido", 0, 5),
    ("t5", "task", "Validar R1, descontar insumos (1 transacción)", 1, 6),
    ("t6", "task", "Preparar líneas por estación", 2, 7),
    ("g2", "exclusiveGateway", "¿Todas las líneas listas?", 2, 8),
    ("t7", "task", "Cerrar pedido y registrar venta", 1, 9),
    ("fin", "endEvent", "Pedido entregado", 0, 10),
    ("t8", "task", "Cancelar con motivo (si aplica)", 3, 5),
    ("fin2", "endEvent", "Pedido cancelado", 3, 6),
]
FLUJOS = [
    ("ini", "t1", ""), ("t1", "t2", ""), ("t2", "g1", ""), ("g1", "t3", "No"), ("t3", "t2", "corregir"),
    ("g1", "t4", "Sí"), ("t4", "t5", ""), ("t5", "t6", ""), ("t6", "g2", ""), ("g2", "t6", "No"),
    ("g2", "t7", "Sí"), ("t7", "fin", ""), ("t4", "t8", "cancelar"), ("t8", "fin2", ""),
]


def centro(n):
    _, tipo, _, carril, col = n
    cx = X0 + col * (W + 30) + W // 2
    cy = carril * LH + LH // 2
    return cx, cy


def caja(n):
    cx, cy = centro(n)
    tipo = n[1]
    if tipo.endswith("Event"):
        return cx - 18, cy - 18, 36, 36
    if tipo == "exclusiveGateway":
        return cx - 25, cy - 25, 50, 50
    return cx - W // 2, cy - H // 2, W, H


def main():
    idx = {n[0]: n for n in NODOS}
    ancho = X0 + 11 * (W + 30)
    x = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL" '
         'xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" '
         'xmlns:di="http://www.omg.org/spec/DD/20100524/DI" id="defs" targetNamespace="http://sazon-urbano/bpmn">',
         '<collaboration id="col"><participant id="part" name="Sazón Urbano (TO-BE)" processRef="proc"/></collaboration>',
         '<process id="proc" isExecutable="false"><laneSet id="ls">']
    for i, nombre in enumerate(LANES):
        refs = "".join(f"<flowNodeRef>{n[0]}</flowNodeRef>" for n in NODOS if n[3] == i)
        x.append(f'<lane id="lane{i}" name="{nombre}">{refs}</lane>')
    x.append("</laneSet>")
    for nid, tipo, nombre, _, _ in NODOS:
        entradas = "".join(f"<incoming>f_{a}_{b}</incoming>" for a, b, _ in FLUJOS if b == nid)
        salidas = "".join(f"<outgoing>f_{a}_{b}</outgoing>" for a, b, _ in FLUJOS if a == nid)
        x.append(f'<{tipo} id="{nid}" name="{nombre}">{entradas}{salidas}</{tipo}>')
    for a, b, et in FLUJOS:
        x.append(f'<sequenceFlow id="f_{a}_{b}" name="{et}" sourceRef="{a}" targetRef="{b}"/>')
    x.append('</process><bpmndi:BPMNDiagram id="d"><bpmndi:BPMNPlane id="p" bpmnElement="col">')
    x.append(f'<bpmndi:BPMNShape id="s_part" bpmnElement="part" isHorizontal="true"><dc:Bounds x="20" y="0" width="{ancho}" '
             f'height="{LH * len(LANES)}"/></bpmndi:BPMNShape>')
    for i in range(len(LANES)):
        x.append(f'<bpmndi:BPMNShape id="s_lane{i}" bpmnElement="lane{i}" isHorizontal="true"><dc:Bounds x="50" y="{i * LH}" '
                 f'width="{ancho - 30}" height="{LH}"/></bpmndi:BPMNShape>')
    for n in NODOS:
        bx, by, bw, bh = caja(n)
        x.append(f'<bpmndi:BPMNShape id="s_{n[0]}" bpmnElement="{n[0]}"><dc:Bounds x="{bx}" y="{by}" width="{bw}" height="{bh}"/>'
                 f'</bpmndi:BPMNShape>')
    for a, b, _ in FLUJOS:
        ax, ay, aw, ah = caja(idx[a])
        bx, by, bw, bh = caja(idx[b])
        p1 = (ax + aw, ay + ah // 2)
        p2 = (bx, by + bh // 2)
        pts = [p1, (p1[0] + 10, p1[1]), (p1[0] + 10, p2[1]), p2] if p2[0] > p1[0] else [
            (ax + aw // 2, ay), (ax + aw // 2, ay - 40), (bx + bw // 2, ay - 40), (bx + bw // 2, by)]
        way = "".join(f'<di:waypoint x="{px}" y="{py}"/>' for px, py in pts)
        x.append(f'<bpmndi:BPMNEdge id="e_{a}_{b}" bpmnElement="f_{a}_{b}">{way}</bpmndi:BPMNEdge>')
    x.append("</bpmndi:BPMNPlane></bpmndi:BPMNDiagram></definitions>")
    DESTINO.write_text("\n".join(x), encoding="utf-8")
    print(f"BPMN generado: {DESTINO}")


if __name__ == "__main__":
    main()
