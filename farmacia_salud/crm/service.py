"""Servicio CRM: detección de clientes en riesgo de deserción."""

from datetime import datetime, timedelta
from core.models import Cliente, AlertaDesercion
from core.repository import get_session


def detectar_clientes_en_riesgo(session, dias_umbral: int = 30) -> list:
    ahora = datetime.now()
    fecha_limite = ahora - timedelta(days=dias_umbral)

    clientes_riesgo = session.query(Cliente).filter(
        Cliente.fecha_ultima_compra < fecha_limite,
        Cliente.fecha_ultima_compra.isnot(None),
    ).all()

    alertas = []
    for cliente in clientes_riesgo:
        dias_sin = (ahora - cliente.fecha_ultima_compra).days
        alerta_existente = session.query(AlertaDesercion).filter_by(
            cliente_id=cliente.id,
            estado="En riesgo"
        ).first()

        if not alerta_existente:
            alerta = AlertaDesercion(
                cliente_id=cliente.id,
                dias_sin_compra=dias_sin,
                estado="En riesgo",
            )
            session.add(alerta)
            alertas.append(alerta)
        else:
            alertas.append(alerta_existente)

    session.commit()
    return alertas


def generar_campana_recuperacion(session, cliente_ids):
    return session.query(AlertaDesercion).filter(
        AlertaDesercion.cliente_id.in_(cliente_ids),
        AlertaDesercion.estado == "En riesgo",
    ).all()
