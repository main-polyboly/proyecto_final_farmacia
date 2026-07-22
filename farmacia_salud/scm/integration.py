"""Integración SCM: suscriptor al evento on_venta_registrada.

Al registrarse una venta:
1. Descuenta stock del producto en la sucursal correspondiente.
2. Si stock resultante < stock_minimo, genera Orden de Compra automática.
"""

from core.models import InventarioSCM, OrdenCompraSCM, ItemOrdenCompraSCM, ProveedorSCM
from core.pos import EventoVenta
from core.repository import get_session
from datetime import datetime, timedelta
import random


PROVEEDORES_SIMULADOS = [
    {"nombre": "FarmaDistribuidora SA", "cuit": "30-12345678-9", "email": "ventas@farmadist.com"},
    {"nombre": "MediSupply SRL", "cuit": "30-87654321-0", "email": "pedidos@medisupply.com"},
]


def _asegurar_proveedores(session):
    proveedores = session.query(ProveedorSCM).all()
    if not proveedores:
        for p in PROVEEDORES_SIMULADOS:
            prov = ProveedorSCM(**p, tiempo_entrega_dias=3)
            session.add(prov)
        session.flush()
        proveedores = session.query(ProveedorSCM).all()
    return proveedores


def procesar_venta_scm(evento: EventoVenta):
    session = get_session()
    try:
        venta = evento.venta
        ordenes_generadas = []

        for detalle in evento.detalles:
            inv = session.query(InventarioSCM).filter_by(
                producto_id=detalle.producto_id,
                sucursal_id=venta.sucursal_id,
            ).first()

            if not inv:
                continue

            inv.stock_actual = max(0, inv.stock_actual - detalle.cantidad)
            inv.ultima_salida = venta.fecha

            if inv.stock_actual < inv.stock_minimo:
                proveedores = _asegurar_proveedores(session)
                proveedor = proveedores[0]
                producto = detalle.producto

                orden = OrdenCompraSCM(
                    proveedor_id=proveedor.id,
                    sucursal_id=venta.sucursal_id,
                    motivo=f"Stock bajo: {producto.nombre if producto else 'prod'} (stock={inv.stock_actual}, min={inv.stock_minimo})",
                    fecha_estimada=venta.fecha + timedelta(days=proveedor.tiempo_entrega_dias),
                    estado="Pendiente",
                )
                session.add(orden)
                session.flush()

                cantidad_sugerida = max(inv.stock_minimo * 2 - inv.stock_actual, 1)
                precio = round(random.uniform(2, 15), 2)
                item = ItemOrdenCompraSCM(
                    orden_compra_id=orden.id,
                    producto_id=detalle.producto_id,
                    proveedor_id=proveedor.id,
                    cantidad=cantidad_sugerida,
                    precio_unitario=precio,
                    subtotal=round(precio * cantidad_sugerida, 2),
                )
                session.add(item)
                orden.total = item.subtotal
                ordenes_generadas.append(orden)

        session.commit()

        for oc in ordenes_generadas:
            print(f"[SCM] Orden de compra #{oc.id} generada - {oc.motivo}")
        if not ordenes_generadas:
            print(f"[SCM] Stock OK para venta {venta.invoice}")
    except Exception as e:
        session.rollback()
        print(f"[SCM] Error procesando venta: {e}")
