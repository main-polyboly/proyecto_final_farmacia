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
from dashboard.charts import (
    generar_dashboard_completo,
    guardar_snapshot_dashboard,
    procesar_venta_dashboard,
)
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
    print("\n" + "=" * 60)
    print("PASO 2: DEMOSTRACION EN VIVO - UNA VENTA, TRES ACTUALIZACIONES")
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

    print("[VENTA] El POS registrara la siguiente transaccion:")
    print(f"        Producto: {producto.nombre} | Cantidad: 5 | Precio unitario: ${precio_unit:.2f}")
    print(f"        Cliente: {cliente.nombre or cliente.customer_id} | Sucursal: {sucursal.nombre}")
    print("[FLUJO] POS -> ERP (caja) -> SCM (stock/OC) -> Dashboard (graficos)" )

    pos = POS(session=session)
    pos.suscribir(procesar_venta_erp)
    pos.suscribir(procesar_venta_scm)
    pos.suscribir(procesar_venta_dashboard)

    from core.models import CajaChica, OrdenCompraSCM
    if not session.query(CajaChica).filter_by(sucursal_id=sucursal.id).first():
        session.add(CajaChica(sucursal_id=sucursal.id, saldo_actual=0))
        session.commit()
    generar_dashboard_completo(session, cargar_datos_rfm(session))
    dashboard_antes = guardar_snapshot_dashboard("dashboard_antes.png")
    print("\n[ESTADO INICIAL - ANTES DE LA VENTA]")
    print("[Dashboard] Snapshot guardado: outputs/dashboard_antes.png")

    caja_antes = session.query(CajaChica).filter_by(sucursal_id=sucursal.id).first()
    stock_antes = session.query(InventarioSCM).filter_by(
        producto_id=producto.id, sucursal_id=sucursal.id
    ).first()
    ordenes_antes = session.query(OrdenCompraSCM).count()
    print(
        f"        Caja ERP: ${(float(caja_antes.saldo_actual) if caja_antes else 0):.2f} | "
        f"Stock SCM: {(stock_antes.stock_actual if stock_antes else 'N/D')} | "
        f"Ordenes SCM: {ordenes_antes}"
    )

    items = [{
        "producto_id": producto.id,
        "cantidad": 5,
        "precio_unitario": precio_unit,
    }]

    venta = pos.registrar_venta(cliente_id=cliente.id, sucursal_id=sucursal.id, items=items)
    if not venta:
        print("Error en la venta.")
        return

    session.expire_all()
    inv = session.query(InventarioSCM).filter_by(producto_id=producto.id, sucursal_id=sucursal.id).first()
    if inv:
        print(f"[SCM] Stock actual {producto.nombre} en {sucursal.nombre}: {inv.stock_actual} (min={inv.stock_minimo})")

    caja_despues = session.query(CajaChica).filter_by(sucursal_id=sucursal.id).first()
    stock_despues = session.query(InventarioSCM).filter_by(
        producto_id=producto.id, sucursal_id=sucursal.id
    ).first()
    oc_count = session.query(OrdenCompraSCM).count()
    print(
        "\n[ESTADO FINAL - DESPUES DE LA VENTA]\n"
        f"        Caja ERP: ${(float(caja_despues.saldo_actual) if caja_despues else 0):.2f} | "
        f"Stock SCM: {(stock_despues.stock_actual if stock_despues else 'N/D')} | "
        f"Ordenes SCM: {oc_count}"
    )
    caja_inicial = float(caja_antes.saldo_actual) if caja_antes else 0
    stock_inicial = stock_antes.stock_actual if stock_antes else 0
    caja_final = float(caja_despues.saldo_actual) if caja_despues else 0
    stock_final = stock_despues.stock_actual if stock_despues else 0
    print("\n[CAMBIOS DETECTADOS]")
    print(f"        ERP: caja ${caja_inicial:.2f} -> ${caja_final:.2f} (+${caja_final - caja_inicial:.2f})")
    print(f"        SCM: stock {stock_inicial} -> {stock_final} (-{stock_inicial - stock_final} unidades)")
    print(f"        SCM: ordenes de compra {ordenes_antes} -> {oc_count}")
    print("        Dashboard: comparar outputs/dashboard_antes.png con outputs/dashboard_despues.png")
    print("\n[DEMO COMPLETADA] Una venta actualizo ERP, SCM y Dashboard automaticamente.")


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
