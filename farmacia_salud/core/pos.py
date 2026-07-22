"""Sistema POS (Punto de Venta) con patrón de eventos para integración."""

from typing import Callable, Dict, List, Optional
from datetime import datetime
from core.repository import get_session, init_db
from core.models import Venta, DetalleVenta, Cliente, Sucursal


class EventoVenta:
    def __init__(self, venta: Venta, detalles: List[DetalleVenta]):
        self.venta = venta
        self.detalles = detalles


class POS:
    def __init__(self, session=None):
        self._suscriptores: List[Callable[[EventoVenta], None]] = []
        self.session = session or get_session()
        init_db()

    def suscribir(self, callback: Callable[[EventoVenta], None]):
        self._suscriptores.append(callback)

    def _disparar(self, evento: EventoVenta):
        for cb in self._suscriptores:
            try:
                cb(evento)
            except Exception as e:
                print(f"[POS] Error en suscriptor: {e}")

    def _obtener_o_crear_cliente(self, customer_id: str) -> Cliente:
        cliente = self.session.query(Cliente).filter_by(customer_id=str(customer_id)).first()
        if not cliente:
            cliente = Cliente(customer_id=str(customer_id))
            self.session.add(cliente)
            self.session.flush()
        return cliente

    def registrar_venta(
        self,
        cliente_id: int,
        sucursal_id: int,
        items: List[Dict],
        metodo_pago: str = "Efectivo",
    ) -> Optional[Venta]:
        try:
            cliente = self.session.query(Cliente).filter_by(id=cliente_id).first()
            if not cliente:
                raise ValueError(f"Cliente {cliente_id} no encontrado")

            total = sum(item["cantidad"] * item["precio_unitario"] for item in items)
            venta = Venta(
                invoice="__TEMP__",
                cliente_id=cliente.id,
                sucursal_id=sucursal_id,
                fecha=datetime.now(),
                total=round(total, 2),
                metodo_pago=metodo_pago,
                estado="Completada",
            )
            self.session.add(venta)
            self.session.flush()
            venta.invoice = f"INV{venta.id:08d}"
            self.session.commit()

            detalles = []
            for item in items:
                subtotal = round(item["cantidad"] * item["precio_unitario"], 2)
                detalle = DetalleVenta(
                    venta_id=venta.id,
                    producto_id=item["producto_id"],
                    cantidad=item["cantidad"],
                    precio_unitario=round(item["precio_unitario"], 2),
                    subtotal=subtotal,
                )
                self.session.add(detalle)
                detalles.append(detalle)

            self.session.commit()

            cliente.fecha_ultima_compra = venta.fecha
            cliente.fecha_primera_compra = cliente.fecha_primera_compra or venta.fecha
            cliente.total_compras = round((cliente.total_compras or 0) + total, 2)
            cliente.frecuencia = (cliente.frecuencia or 0) + 1
            self.session.commit()

            evento = EventoVenta(venta=venta, detalles=detalles)
            self._disparar(evento)

            print(f"[POS] Venta registrada: {venta.invoice} - Total: ${venta.total:.2f}")
            return venta

        except Exception as e:
            self.session.rollback()
            print(f"[POS] Error registrando venta: {e}")
            return None

    def obtener_sucursales(self) -> List[Sucursal]:
        return self.session.query(Sucursal).all()

    def obtener_ventas_por_sucursal(self, sucursal_id: int) -> List[Venta]:
        return self.session.query(Venta).filter_by(sucursal_id=sucursal_id).all()
