"""Integracion ERP: suscriptor al evento on_venta_registrada.

Cada vez que se registra una venta:
1. Crea un asiento contable de ingreso.
2. Actualiza el saldo de caja chica de la sucursal correspondiente.
3. Registra un movimiento de caja.
"""

from core.models import AsientoContable, MovimientoCaja, CajaChica, Sucursal
from core.repository import get_session
from datetime import datetime


def _obtener_o_crear_caja(session, sucursal_id):
    caja = session.query(CajaChica).filter_by(sucursal_id=sucursal_id).first()
    if not caja:
        caja = CajaChica(sucursal_id=sucursal_id, saldo_actual=0)
        session.add(caja)
        session.flush()
    return caja


def procesar_venta_erp(evento):
    session = get_session()
    try:
        venta = evento.venta
        caja = _obtener_o_crear_caja(session, venta.sucursal_id)

        asiento = AsientoContable(
            venta_id=venta.id,
            caja_chica_id=caja.id,
            tipo="Ingreso",
            monto=venta.total,
            descripcion=f"Ingreso por venta {venta.invoice} - Sucursal {venta.sucursal_id}",
        )
        session.add(asiento)
        session.flush()

        caja.saldo_actual = round((caja.saldo_actual or 0) + venta.total, 2)
        caja.ultima_actualizacion = venta.fecha

        mov = MovimientoCaja(
            caja_chica_id=caja.id,
            tipo="Ingreso",
            monto=venta.total,
            concepto=f"Venta {venta.invoice}",
            asiento_id=asiento.id,
        )
        session.add(mov)
        session.commit()

        print(f"[ERP] Asiento generado: {venta.invoice} | ${venta.total:.2f} | Caja suc {venta.sucursal_id}: ${caja.saldo_actual:.2f}")
    except Exception as e:
        session.rollback()
        print(f"[ERP] Error procesando venta: {e}")
