"""Unit of Work sobre una sesión SQLAlchemy: una transacción por operación del servicio."""

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError

from src.application import ports
from src.domain.errors import ConflictoDeConcurrencia
from src.infrastructure.modelos import EventoRow, VentaRow
from src.infrastructure.repositorios import (
    ClienteRepositorioSql,
    IngredienteRepositorioSql,
    PedidoRepositorioSql,
    ProductoRepositorioSql,
    PromocionRepositorioSql,
)


class RelojDelSistema(ports.IReloj):
    """Hora local del restaurante (sin zona horaria en la base: datetime ingenuo y local)."""

    def __init__(self, zona: str = "America/Monterrey"):
        self._zona = ZoneInfo(zona)

    def ahora(self) -> datetime:
        return datetime.now(self._zona).replace(tzinfo=None, microsecond=0)


class UnidadDeTrabajoSql(ports.IUnitOfWork):
    def __init__(self, fabrica_de_sesiones, publicador: ports.IPublicadorDeEventos):
        self._fabrica = fabrica_de_sesiones
        self._publicador = publicador
        self._eventos: list = []

    def __enter__(self):
        self.sesion = self._fabrica()
        self.pedidos = PedidoRepositorioSql(self.sesion)
        self.productos = ProductoRepositorioSql(self.sesion)
        self.ingredientes = IngredienteRepositorioSql(self.sesion)
        self.promociones = PromocionRepositorioSql(self.sesion)
        self.clientes = ClienteRepositorioSql(self.sesion)
        self._eventos = []
        return self

    def __exit__(self, tipo, valor, traza):
        if tipo is not None:
            self.sesion.rollback()
        self.sesion.close()
        return False

    def registrar_eventos(self, eventos):
        self._eventos.extend(eventos)

    def confirmar(self):
        for evento in self._eventos:  # bitácora de eventos en la misma transacción
            self.sesion.add(
                EventoRow(
                    nombre=evento.nombre,
                    agregado_id=evento.agregado_id,
                    usuario=evento.usuario,
                    ocurrido_en=evento.ocurrido_en,
                    detalle=evento.detalle,
                )
            )
        try:
            self.sesion.commit()
        except IntegrityError as exc:
            self.sesion.rollback()
            raise ConflictoDeConcurrencia("El registro ya existe o cambió; reintente.") from exc
        eventos, self._eventos = self._eventos, []
        self._publicador.publicar(eventos)  # solo después de confirmar la transacción

    def revertir(self):
        self.sesion.rollback()
        self._eventos = []


class PublicadorEnMemoria(ports.IPublicadorDeEventos):
    """Bus de eventos simple: llama a los suscriptores después del commit."""

    def __init__(self):
        self._suscriptores: dict = {}

    def suscribir(self, nombre_evento: str, manejador):
        self._suscriptores.setdefault(nombre_evento, []).append(manejador)

    def publicar(self, eventos):
        for evento in eventos:
            for manejador in self._suscriptores.get(evento.nombre, []):
                manejador(evento)


class ActualizadorDeVentas:
    """Suscriptor de PedidoCerrado: genera el modelo de lectura VentaResumen (ADR-04)."""

    def __init__(self, fabrica_de_sesiones):
        self._fabrica = fabrica_de_sesiones

    def __call__(self, evento):
        from decimal import Decimal

        with self._fabrica() as sesion:
            if sesion.get(VentaRow, evento.agregado_id) is None:
                sesion.add(
                    VentaRow(
                        pedido_id=evento.agregado_id,
                        canal=evento.detalle["canal"],
                        fecha_cierre=evento.ocurrido_en,
                        total_productos=evento.detalle["unidades"],
                        total_importe=Decimal(evento.detalle["total"]),
                    )
                )
                sesion.commit()
