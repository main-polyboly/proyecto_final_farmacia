"""Cargador de datos CSV a SQLite.

Decisiones de diseño documentadas:
- Clientes: customer_id sintético generado aleatoriamente (1..500).
- Precios: generados por dosage_form con valores realistas.
- Cantidad: columna Sales_Sheet.
- dosage_form nulo: rellenado con 'Otro'.
"""

import os
import random
import pandas as pd
import numpy as np
from datetime import datetime
from core.repository import get_session, init_db
from core.models import (
    Producto, Precio, Sucursal, Cliente, Venta, DetalleVenta,
    Proveedor, InventarioSCM
)

random.seed(42)
np.random.seed(42)


PRECIOS_BY_DOSAGE = {
    "Tablet": (2.0, 5.0),
    "Capsule": (3.0, 8.0),
    "Cream": (4.0, 10.0),
    "Shampoo": (5.0, 12.0),
    "Ointment": (3.0, 9.0),
    "Syrup": (4.0, 8.0),
    "Injectable": (8.0, 20.0),
    "Drops": (3.0, 7.0),
    "Otro": (2.0, 15.0),
}


def generar_precios(dosage_forms):
    precios = {}
    for form in dosage_forms:
        low, high = PRECIOS_BY_DOSAGE.get(form, (2.0, 15.0))
        precios[form] = round(random.uniform(low, high), 2)
    return precios


def parse_fecha(fecha_str):
    for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(fecha_str), fmt)
        except ValueError:
            continue
    return None


def cargar_csvs(session, csv_paths):
    print(f"Cargando {len(csv_paths)} archivos CSV reducidos...")
    all_chunks = []
    for path in csv_paths:
        df = pd.read_csv(path, dtype={"Invoice": str, "barcode": str})
        all_chunks.append(df)

    df = pd.concat(all_chunks, ignore_index=True)
    print(f"Total filas brutas: {len(df)}")

    df.columns = [c.strip() for c in df.columns]

    if "doage_form" in df.columns:
        df.rename(columns={"doage_form": "dosage_form"}, inplace=True)

    df["dosage_form"] = df["dosage_form"].fillna("Otro").str.strip()
    df["Sales_Sheet"] = pd.to_numeric(df["Sales_Sheet"], errors="coerce").fillna(1).astype(int)
    df["addeddate"] = df["addeddate"].astype(str).apply(parse_fecha)
    df = df[df["addeddate"].notna()].copy()

    sucursales_map = {
        "Ph01": ("Sucursal 01", "Z01", "City1"),
        "Ph02": ("Sucursal 02", "Z02", "City1"),
        "Ph03": ("Sucursal 03", "Z03", "City1"),
        "Ph04": ("Sucursal 04", "Z01", "City2"),
    }

    for name, zona, ciudad in sucursales_map.values():
        if not session.query(Sucursal).filter_by(nombre=name).first():
            session.add(Sucursal(nombre=name, zona=zona, ciudad=ciudad))
    session.commit()
    sucs = {s.nombre: s.id for s in session.query(Sucursal).all()}

    dosage_forms = df["dosage_form"].unique().tolist()
    precios_map = generar_precios(dosage_forms)

    productos_cache = {}
    for _, row in df.drop_duplicates(subset=["barcode"]).iterrows():
        barcode = str(row["barcode"])
        if barcode not in productos_cache:
            prod = Producto(
                barcode=barcode,
                nombre=row["name"],
                dosage_form=row["dosage_form"],
                tipo=row["type"],
            )
            session.add(prod)
            try:
                session.flush()
            except Exception:
                session.rollback()
                continue
            precio = Precio(producto_id=prod.id, precio_unitario=precios_map.get(row["dosage_form"], 10.0))
            session.add(precio)
            productos_cache[barcode] = (prod.id, row["dosage_form"])

    session.commit()
    productos_db = {p.barcode: p for p in session.query(Producto).all()}

    umbral_stock_default = 10
    for prod in session.query(Producto).all():
        for suc_id in sucs.values():
            if not session.query(InventarioSCM).filter_by(producto_id=prod.id, sucursal_id=suc_id).first():
                session.add(InventarioSCM(
                    producto_id=prod.id,
                    sucursal_id=suc_id,
                    stock_actual=random.randint(50, 200),
                    stock_minimo=umbral_stock_default,
                ))

    session.commit()

    df["customer_id"] = df.groupby("Invoice").ngroup() % 500 + 1
    df["customer_id"] = df["customer_id"].astype(str)
    df["subtotal"] = df["Sales_Sheet"] * df["dosage_form"].map(precios_map)

    invoice_groups = df.groupby("Invoice")
    for invoice, group in invoice_groups:
        branch_code = None
        for suffix in ["Ph01", "Ph02", "Ph03", "Ph04"]:
            if any(suffix in str(x) for x in group.index):
                branch_code = suffix
                break
        if branch_code is None:
            branch_code = "Ph01"

        suc_nombre, _, _ = sucursales_map.get(branch_code, ("Sucursal 01", "Z01", "City1"))
        suc_id = sucs.get(suc_nombre)

        cliente_id = int(group["customer_id"].iloc[0])
        fecha = group["addeddate"].iloc[0]
        total = group["subtotal"].sum()

        venta = Venta(
            invoice=str(invoice),
            cliente_id=cliente_id,
            sucursal_id=suc_id,
            fecha=fecha,
            total=round(total, 2),
            estado="Completada",
        )
        session.add(venta)
        session.flush()
        for _, det in group.iterrows():
            producto = productos_db.get(str(det["barcode"]))
            if producto is None:
                continue
            subtotal = round(det["subtotal"], 2)
            detalle = DetalleVenta(
                venta_id=venta.id,
                producto_id=producto.id,
                cantidad=int(det["Sales_Sheet"]),
                precio_unitario=round(subtotal / max(int(det["Sales_Sheet"]), 1), 2),
                subtotal=subtotal,
            )
            session.add(detalle)

    session.commit()
    print("Carga de CSV finalizada.")


def main():
    init_db()
    session = get_session()

    data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "PharmacyTransactionalDataset")
    csv_paths = []
    for root, dirs, files in os.walk(data_dir):
        for f in files:
            if f.endswith(".csv") and f != "global_test_set.csv":
                csv_paths.append(os.path.join(root, f))

    cargar_csvs(session, csv_paths)
    print(f"Sucursales: {session.query(Sucursal).count()}")
    print(f"Productos: {session.query(Producto).count()}")
    print(f"Ventas: {session.query(Venta).count()}")
    print(f"Clientes únicos: {session.query(Cliente).count()}")
    print(f"Inventario registros: {session.query(InventarioSCM).count()}")


if __name__ == "__main__":
    main()
