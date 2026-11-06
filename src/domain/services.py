"""Domain Services: reglas que cruzan Aggregates y no pertenecen a uno solo (informe U3, Tabla 20)."""

from collections import defaultdict
from collections.abc import Iterable, Mapping
from decimal import Decimal

from src.domain.entities import Ingrediente, Pedido, Producto, Promocion
from src.domain.specifications import EvaluacionPedido
from src.domain.value_objects import Disponibilidad


class DisponibilidadProductos:
    """RN-02 y RN-12: un producto está disponible si no está agotado y sus ingredientes alcanzan."""

    def evaluar(
        self, producto: Producto, cantidad: int, ingredientes: Mapping[str, Ingrediente]
    ) -> Disponibilidad:
        if producto.agotado:
            return Disponibilidad.no(f"{producto.nombre} está agotado")
        for req in producto.receta:
            ingrediente = ingredientes.get(req.ingrediente_id)
            if ingrediente is None:
                return Disponibilidad.no(f"falta el ingrediente {req.ingrediente_id}")
            if ingrediente.existencia < req.cantidad * cantidad:
                return Disponibilidad.no(
                    f"ingredientes insuficientes para {producto.nombre}: {ingrediente.nombre}"
                )
        return Disponibilidad.si()


class ConsumoDeIngredientes:
    """RN-10, RN-12, SP-04, SP-08: descuenta o reintegra según la receta de cada línea."""

    def necesidades(self, pedido: Pedido, productos: Mapping[str, Producto]) -> dict:
        total = defaultdict(Decimal)
        for linea in pedido.lineas:
            for req in productos[linea.producto_id].receta:
                total[req.ingrediente_id] += req.cantidad * linea.cantidad
        return dict(total)

    def descontar(self, pedido, productos, ingredientes, usuario, ahora):
        for ingrediente_id, cantidad in self.necesidades(pedido, productos).items():
            ingredientes[ingrediente_id].registrar_salida(
                cantidad, usuario, ahora, referencia=f"pedido {pedido.pedido_id}"
            )

    def reintegrar(self, pedido, productos, ingredientes, usuario, ahora):
        for ingrediente_id, cantidad in self.necesidades(pedido, productos).items():
            ingredientes[ingrediente_id].registrar_entrada(
                cantidad, usuario, ahora, referencia=f"cancelación {pedido.pedido_id}"
            )


class EvaluadorPromociones:
    """RN-13: decide qué promoción aplica a un pedido según horario y condiciones."""

    def aplicable(
        self, evaluacion: EvaluacionPedido, promociones: Iterable[Promocion]
    ) -> Promocion | None:
        candidatas = [promo for promo in promociones if promo.evaluar(evaluacion)]
        if not candidatas:
            return None
        return max(candidatas, key=lambda promo: promo.descuento_pct)
