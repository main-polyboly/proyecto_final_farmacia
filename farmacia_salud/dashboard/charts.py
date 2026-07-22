"""Dashboard con 3 gráficos: evolución de ventas, segmentos RFM, KPI ERP."""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import pandas as pd

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def grafico_evolucion_ventas(session, guardar=True):
    from core.models import Venta

    ventas = session.query(Venta).all()
    if not ventas:
        return None

    df = pd.DataFrame([
        {"fecha": pd.to_datetime(v.fecha) if v.fecha else None, "total": float(v.total or 0), "sucursal_id": v.sucursal_id}
        for v in ventas
    ])
    df = df.dropna()
    if df.empty:
        return None

    df = df.sort_values("fecha")
    df_sem = df.groupby(["fecha", "sucursal_id"])["total"].sum().reset_index()
    pivot = df_sem.pivot(index="fecha", columns="sucursal_id", values="total").fillna(0)
    pivot.index = pd.to_datetime(pivot.index)
    pivot = pivot.resample("W").sum()

    fig, ax = plt.subplots(figsize=(10, 5))
    pivot.plot(ax=ax, marker="o")
    ax.set_title("Evolución semanal de ventas por sucursal")
    ax.set_xlabel("Semana")
    ax.set_ylabel("Ventas ($)")
    ax.legend(title="Sucursal", loc="upper left")
    fig.tight_layout()

    if guardar:
        fig.savefig(os.path.join(OUTPUT_DIR, "01_evolucion_ventas.png"), dpi=150)
        fig.savefig(os.path.join(OUTPUT_DIR, "01_evolucion_ventas.pdf"), dpi=150)
    plt.close(fig)
    return fig


def grafico_segmentos_rfm(rfm_df, guardar=True):
    if rfm_df is None or rfm_df.empty:
        return None

    counts = rfm_df["Segmento"].value_counts().reindex(["VIP", "Fieles", "En Riesgo", "Perdidos"]).fillna(0)

    fig, ax = plt.subplots(figsize=(8, 5))
    counts.plot(kind="bar", color=["#2ecc71", "#3498db", "#f1c40f", "#e74c3c"], ax=ax)
    ax.set_title("Segmentación RFM de clientes")
    ax.set_xlabel("Segmento")
    ax.set_ylabel("Cantidad de clientes")
    plt.xticks(rotation=0)
    fig.tight_layout()

    if guardar:
        fig.savefig(os.path.join(OUTPUT_DIR, "02_segmentos_rfm.png"), dpi=150)
        fig.savefig(os.path.join(OUTPUT_DIR, "02_segmentos_rfm.pdf"), dpi=150)
    plt.close(fig)
    return fig


def grafico_kpi_erp(session, guardar=True):
    from core.models import CajaChica, OrdenCompraSCM

    cajas = session.query(CajaChica).all()
    if not cajas:
        return None

    df_caja = pd.DataFrame([
        {"sucursal_id": c.sucursal_id, "saldo": float(c.saldo_actual or 0)}
        for c in cajas
    ])
    ocs = session.query(OrdenCompraSCM).all()
    df_oc = pd.DataFrame([
        {"sucursal_id": oc.sucursal_id, "monto_oc": float(oc.total or 0)}
        for oc in ocs
    ])
    if not df_oc.empty:
        df_oc_sum = df_oc.groupby("sucursal_id")["monto_oc"].sum().reset_index()
        df_caja = df_caja.merge(df_oc_sum, on="sucursal_id", how="left").fillna(0)
    else:
        df_caja["monto_oc"] = 0

    fig, ax = plt.subplots(figsize=(8, 5))
    x = range(len(df_caja))
    width = 0.35
    ax.bar([i - width/2 for i in x], df_caja["saldo"], width, label="Saldo caja chica ($)", color="#3498db")
    ax.bar([i + width/2 for i in x], df_caja["monto_oc"], width, label="Órdenes de compra ($)", color="#e67e22")
    ax.set_title("KPI ERP/SCM: Caja chica vs. Órdenes de compra por sucursal")
    ax.set_xlabel("Sucursal ID")
    ax.set_ylabel("Monto ($)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(df_caja["sucursal_id"].tolist())
    ax.legend()
    fig.tight_layout()

    if guardar:
        fig.savefig(os.path.join(OUTPUT_DIR, "03_kpi_erp_scm.png"), dpi=150)
        fig.savefig(os.path.join(OUTPUT_DIR, "03_kpi_erp_scm.pdf"), dpi=150)
    plt.close(fig)
    return fig


def generar_dashboard_completo(session, rfm_df=None):
    grafico_evolucion_ventas(session)
    grafico_segmentos_rfm(rfm_df)
    grafico_kpi_erp(session)

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle("Dashboard gerencial - Farmacia", fontsize=16)

    for ax in axes:
        ax.axis("off")

    img1 = plt.imread(os.path.join(OUTPUT_DIR, "01_evolucion_ventas.png"))
    img2 = plt.imread(os.path.join(OUTPUT_DIR, "02_segmentos_rfm.png"))
    img3 = plt.imread(os.path.join(OUTPUT_DIR, "03_kpi_erp_scm.png"))

    axes[0].imshow(img1)
    axes[0].axis("on")
    axes[1].imshow(img2)
    axes[1].axis("on")
    axes[2].imshow(img3)
    axes[2].axis("on")

    plt.tight_layout()
    combined_path = os.path.join(OUTPUT_DIR, "dashboard_completo.png")
    fig.savefig(combined_path, dpi=150)
    plt.close(fig)
    print(f"[Dashboard] Panel combinado guardado en {combined_path}")
