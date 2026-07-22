"""
Main: demo de integracion Core -> ERP -> SCM -> CRM + Dashboard + RFM + Informe.
"""

import os
from datetime import datetime

from core.repository import init_db, get_session
from core.loader import cargar_csvs
from core.pos import POS, EventoVenta
from core.models import Sucursal, Cliente, Producto, Precio, InventarioSCM
from erp.integration import procesar_venta_erp
from scm.integration import procesar_venta_scm
from crm.service import detectar_clientes_en_riesgo
from bi.rfm import cargar_datos_rfm
from dashboard.charts import generar_dashboard_completo
from reports.informe_manager import generar_informe_texto


DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "datasets_reducidos"))


def paso1_cargar_datos():
    print("=" * 60)
    print("PASO 1: Carga de datos CSV a SQLite")
    print("=" * 60)
    init_db(drop=True)
    session = get_session()
    csv_paths = []
    for root, dirs, files in os.walk(DATA_DIR):
        for f in files:
            if f.endswith(".csv") and f != "global_test_set.csv":
                csv_paths.append(os.path.join(root, f))
    cargar_csvs(session, csv_paths)
    print(f"Sucursales: {session.query(Sucursal).count()}")
    print(f"Productos: {session.query(Producto).count()}")
    print(f"Ventas: {session.query(__import__('core.models', fromlist=['Venta']).Venta).count()}")
    print(f"InventarioSCM: {session.query(InventarioSCM).count()}")
    print()


def paso2_demo_integracion():
    print("=" * 60)
    print("PASO 2: Demo - Transaccion real con integracion automatica")
    print("=" * 60)
    from core.models import Venta

    session = get_session()
    producto = session.query(Producto).first()
    if not producto:
        print("Sin productos cargados.")
        return
    sucursal = session.query(Sucursal).first()
    cliente = session.query(Cliente).first()
    if not cliente:
        cliente = Cliente(customer_id="999", nombre="Cliente Demo")
        session.add(cliente)
        session.commit()

    precio = session.query(Precio).filter_by(producto_id=producto.id).first()
    precio_unit = float(precio.precio_unitario) if precio else 10.0

    pos = POS(session=session)
    pos.suscribir(procesar_venta_erp)
    pos.suscribir(procesar_venta_scm)

    items = [{
        "producto_id": producto.id,
        "cantidad": 5,
        "precio_unitario": precio_unit,
    }]

    venta = pos.registrar_venta(cliente_id=cliente.id, sucursal_id=sucursal.id, items=items)
    if not venta:
        print("Error en la venta.")
        return

    inv = session.query(InventarioSCM).filter_by(producto_id=producto.id, sucursal_id=sucursal.id).first()
    if inv:
        print(f"[SCM] Stock actual {producto.nombre} en {sucursal.nombre}: {inv.stock_actual} (min={inv.stock_minimo})")

    from core.models import OrdenCompra
    oc_count = session.query(OrdenCompra).count()
    print(f"[SCM] Ordenes de compra generadas: {oc_count}")
    print(f"[SCM] Demo completada - Una venta -> ERP actualiza caja, SCM descuenta stock y posible OC")


def paso3_crm():
    print("\n" + "=" * 60)
    print("PASO 3: CRM - Deteccion de clientes en riesgo")
    print("=" * 60)
    session = get_session()
    alertas = detectar_clientes_en_riesgo(session, dias_umbral=30)
    print(f"[CRM] Alertas generadas: {len(alertas)}")


def paso4_bi():
    print("\n" + "=" * 60)
    print("PASO 4: BI - Segmentacion RFM")
    print("=" * 60)
    session = get_session()
    rfm_df = cargar_datos_rfm(session)
    if rfm_df is not None and not rfm_df.empty:
        print(rfm_df.groupby("Segmento")["cliente_id"].count().to_string())
    else:
        print("Sin datos para RFM.")
        rfm_df = None
    return rfm_df


def paso5_dashboard(rfm_df=None):
    print("\n" + "=" * 60)
    print("PASO 5: Dashboard - Generacion de graficos")
    print("=" * 60)
    session = get_session()
    generar_dashboard_completo(session, rfm_df)


def paso6_informe():
    print("\n" + "=" * 60)
    print("PASO 6: Informe preliminar")
    print("=" * 60)
    generar_informe_texto()


def main():
    paso1_cargar_datos()
    paso2_demo_integracion()
    paso3_crm()
    rfm_df = paso4_bi()
    paso5_dashboard(rfm_df)
    paso6_informe()
    print("\nFinalizado.")


if __name__ == "__main__":
    main()
