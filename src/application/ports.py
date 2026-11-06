"""Puertos de la capa de aplicación (informe U3, secciones 6 y 7). El dominio no conoce SQL."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Rol(str, Enum):
    MESERO = "MESERO"
    COCINERO = "COCINERO"
    ENCARGADO = "ENCARGADO"
    GERENTE = "GERENTE"


class Accion(str, Enum):
    REGISTRAR_PEDIDOS = "REGISTRAR_PEDIDOS"
    CANCELAR_PEDIDO = "CANCELAR_PEDIDO"
    OPERAR_COCINA = "OPERAR_COCINA"
    GESTIONAR_INVENTARIO = "GESTIONAR_INVENTARIO"
    GESTIONAR_CATALOGO = "GESTIONAR_CATALOGO"
    GESTIONAR_PROMOCIONES = "GESTIONAR_PROMOCIONES"
    CONSULTAR_REPORTES = "CONSULTAR_REPORTES"
    ADMINISTRAR_DATOS = "ADMINISTRAR_DATOS"


@dataclass(frozen=True)
class Usuario:
    """El dominio solo recibe un identificador de usuario y su rol (SP-09)."""

    usuario_id: str
    rol: Rol


class IAutorizador(ABC):
    @abstractmethod
    def puede(self, usuario: Usuario, accion: Accion) -> bool: ...


class IReloj(ABC):
    @abstractmethod
    def ahora(self) -> datetime: ...


class IPublicadorDeEventos(ABC):
    @abstractmethod
    def publicar(self, eventos: list) -> None: ...


class IPedidoRepository(ABC):
    @abstractmethod
    def obtener_por_id(self, pedido_id): ...

    @abstractmethod
    def agregar(self, pedido): ...

    @abstractmethod
    def guardar(self, pedido): ...


class IProductoRepository(ABC):
    @abstractmethod
    def obtener_por_id(self, producto_id): ...

    @abstractmethod
    def obtener_por_ids(self, producto_ids): ...

    @abstractmethod
    def guardar(self, producto): ...


class IIngredienteRepository(ABC):
    @abstractmethod
    def obtener_por_id(self, ingrediente_id): ...

    @abstractmethod
    def obtener_por_ids(self, ingrediente_ids): ...

    @abstractmethod
    def guardar(self, ingrediente): ...


class IPromocionRepository(ABC):
    @abstractmethod
    def obtener_vigentes(self, momento): ...

    @abstractmethod
    def obtener_por_id(self, promocion_id): ...

    @abstractmethod
    def guardar(self, promocion): ...


class IClienteRepository(ABC):
    @abstractmethod
    def obtener_por_id(self, cliente_id): ...

    @abstractmethod
    def guardar(self, cliente): ...


class IUnitOfWork(ABC):
    """Agrupa los cambios de una operación en una sola transacción (una por método)."""

    pedidos: IPedidoRepository
    productos: IProductoRepository
    ingredientes: IIngredienteRepository
    promociones: IPromocionRepository
    clientes: IClienteRepository

    @abstractmethod
    def __enter__(self): ...

    @abstractmethod
    def __exit__(self, tipo, valor, traza): ...

    @abstractmethod
    def registrar_eventos(self, eventos: list) -> None: ...

    @abstractmethod
    def confirmar(self) -> None:
        """Confirma la transacción y después publica los eventos recolectados."""

    @abstractmethod
    def revertir(self) -> None: ...


# --- Lado de lectura (CQRS): interfaces separadas de las de escritura (SOLID-06) ------------
class IConsultasDePedidos(ABC):
    @abstractmethod
    def ordenes_de_estacion(self, estacion): ...

    @abstractmethod
    def historial(self, pedido_id): ...

    @abstractmethod
    def obtener(self, pedido_id): ...

    @abstractmethod
    def listar(self, estado, limite): ...


class IConsultasDeInventario(ABC):
    @abstractmethod
    def disponibilidad_de_productos(self): ...

    @abstractmethod
    def ingredientes(self): ...

    @abstractmethod
    def ingredientes_criticos(self): ...

    @abstractmethod
    def comparativo(self, desde, hasta): ...


class IConsultasDeVentas(ABC):
    @abstractmethod
    def ventas_por_periodo(self, desde, hasta): ...
