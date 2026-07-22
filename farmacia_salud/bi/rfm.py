"""Análisis RFM: Recencia, Frecuencia, Monetario y segmentación."""

import pandas as pd
import numpy as np
from datetime import datetime
from core.repository import get_session
from core.models import Venta, DetalleVenta, Producto, Precio


def cargar_datos_rfm(session):
    ventas = session.query(Venta).all()
    detalles = session.query(DetalleVenta).all()

    precios = {(p.producto_id): p.precio_unitario for p in session.query(Precio).all() if p.precio_unitario}

    detalles_df = pd.DataFrame([
        {
            "venta_id": d.venta_id,
            "producto_id": d.producto_id,
            "cantidad": d.cantidad,
            "subtotal": d.subtotal,
        }
        for d in detalles
    ])

    if detalles_df.empty:
        return pd.DataFrame()

    ventas_df = pd.DataFrame([
        {
            "id": v.id,
            "cliente_id": v.cliente_id,
            "fecha": v.fecha,
            "total": v.total,
        }
        for v in ventas
    ])

    df = detalles_df.merge(ventas_df, left_on="venta_id", right_on="id", how="left")

    rfm = df.groupby("cliente_id").agg(
        Recencia=("fecha", lambda x: (datetime.now() - x.max()).days),
        Frecuencia=("venta_id", "nunique"),
        Monetario=("subtotal", "sum"),
    ).reset_index()

    rfm.columns = ["cliente_id", "Recencia", "Frecuencia", "Monetario"]

    rfm["R_score"] = pd.qcut(rfm["Recencia"], 4, labels=[4, 3, 2, 1]).astype(int)
    rfm["F_score"] = pd.qcut(rfm["Frecuencia"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
    rfm["M_score"] = pd.qcut(rfm["Monetario"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)

    rfm["RFM_Score"] = rfm["R_score"] * 100 + rfm["F_score"] * 10 + rfm["M_score"]

    condiciones = [
        (rfm["RFM_Score"] >= 344),
        (rfm["RFM_Score"] >= 244),
        (rfm["RFM_Score"] >= 144),
        (rfm["RFM_Score"] < 144),
    ]
    etiquetas = ["VIP", "Fieles", "En Riesgo", "Perdidos"]
    rfm["Segmento"] = np.select(condiciones, etiquetas, default="Perdidos")

    return rfm


def resumen_segmentos(rfm_df):
    return rfm_df.groupby("Segmento").agg(
        clientes=("cliente_id", "count"),
        recencia_prom=("Recencia", "mean"),
        frecuencia_prom=("Frecuencia", "mean"),
        monetario_prom=("Monetario", "mean"),
    ).reset_index()
