# Informe de Estrategia y Diseño — FarmaVida
**Firma Consultora INNOVATE TECH**  
**Proyecto Final ISID223 — Transformación Digital Empresarial**

---

## 1. Análisis de las 5 Fuerzas de Porter

### Rivalidad entre competidores (Alta)
FarmaVida compite contra cadenas grandes (farmacias de escala, sucursales multiples) y contra la venta online (marketplaces, delivery). La competencia se da por precio, ubicación y variedad de stock. La rivalidad es alta porque el mercado farmacéutico es maduro y los clientes migran fácilmente ante pequeñas diferencias.

### Amenaza de nuevos entrantes (Moderada)
Barreras moderadas: regulación, necesidad de stock y permisos, pero un competidor digital puede entrar sin sucursal física. No es la amenaza principal hoy, pero hay que blindarse con lealtad y datos.

### Amenaza de productos sustitutos (Alta)
Existe sustitucion por medicamentos genericos, venta por app, delivery propio de cadenas grandes, y productos de cuidado personal por canal no especializado. El cliente puede abandonar la farmacia barrial por conveniencia o precio.

### Poder de negociación de los clientes (Alto)
Los clientes tienen informacion y comparan precios; fidelizacion baja. Sin historial ni beneficios personalizados, migran facilmente. El sistema debe permitir campañas segmentadas para retener.

### Poder de negociacion de los proveedores (Moderado-Alto)
Laboratorios y distribuidores concentrados. Riesgo de desabastecimiento si no hay control de inventario ni proveedores alternativos. El SCM mitiga esto anticipando reposiciones.

**Conclusión**: La integracion de sistemas reduce costos de stock, agiliza la reposicion, y permite segmentar clientes para fidelizar. La informacion pasa de ser un costo a ser ventaja competitiva.

---

## 2. Cadena de Valor

### Actual (manual / desconectada)
- Logística de entrada: pedidos por llamada o papel, stock por sucursal sin visibilidad central.
- Operaciones/venta: registro manual, sin integracion con inventario ni finanzas.
- Logistica de salida: entrega física en mostrador, sin seguimiento.
- Marketing y ventas: no hay datos de clientes; no se segmenta.
- Servicio postventa: sin historial ni alertas.

### Propuesta (digital / integrada)
- Logística de entrada: alertas automáticas SCM, órdenes de compra generadas al detectar stock bajo.
- Operaciones/venta: POS por sucursal que descuenta stock y genera asiento contable en un solo paso.
- Marketing y ventas: segmentación RFM, alertas CRM para recuperacion.
- Servicio postventa: historial por cliente, trazabilidad completa de transacciones.

---

## 3. Requerimientos

### Funcionales (mínimo 8)
1. El sistema debe permitir registrar ventas por sucursal con líneas de producto y cliente asociado.
2. El sistema debe generar automáticamente un asiento contable por cada venta en el modulo ERP.
3. El sistema debe actualizar el saldo de caja chica de la sucursal correspondiente al registrar una venta.
4. El sistema debe descontar stock del producto vendido en la sucursal correspondiente.
5. El sistema debe generar una orden de compra automatica cuando el stock resultante sea menor al minimo definido.
6. El sistema debe permitir consultar clientes en riesgo de desercion segun dias sin compra (CRM).
7. El sistema debe calcular la segmentación RFM sobre el historico de ventas.
8. El sistema debe mostrar un dashboard con evolucion de ventas, distribucion RFM y un KPI ERP/SCM.
9. El sistema debe operar con clientes sintéticos generados con distribucion Pareto (20% de clientes concentran ~60-70% de las compras).
10. El sistema debe calcular montos de venta usando una tabla de precios de referencia por dosage_form, dado que el dataset no incluye precios.

### No funcionales (mínimo 5)
1. Rendimiento: el registro de una venta no debe superar los 2 segundos end-to-end.
2. Disponibilidad: sistema accesible durante horario comercial (>99% uptime en producción).
3. Escalabilidad: soporte para 4 sucursales en MVP; arquitectura preparada para crecer a N sucursales.
4. Usabilidad: interfaz de POS simple para personal no tecnico.
5. Seguridad: cifrado de datos sensibles (clientes, precios) y control de acceso por rol.
6. Mantenibilidad: codigo modular por dominios (Core, ERP, SCM, CRM) sin ciclos de dependencia cruzada.

---

## 4. Integración de módulos (evidencia contra silos)

En una arquitectura integrada, cada modulo se construye alrededor del evento de negocio principal: la venta. El modulo Core expone un mecanismo de publicacion/suscripcion (`on_venta_registrada`). Cuando se registra una venta, Core notifica a ERP, SCM y CRM sin intervencion manual. ERP crea el asiento y actualiza caja en la misma transaccion. SCM descuenta stock y, si corresponde, genera la orden de compra. CRM consulta periodicamente o bajo demanda para marcar clientes inactivos. Asi, la informacion fluye una sola vez y todos los modulos ven la realidad alineada. Si en el futuro se agrega un modulo nuevo (por ejemplo, envios o fidelizacion), se suscribe al mismo evento sin tocar el Core.

---

## 5. Diagrama Entidad-Relación

**Entidades principales:**

- **Cliente** (id, customer_id, nombre, email, telefono, fecha_ultima_compra, segmento_rfm)
- **Producto** (id, barcode, nombre, dosage_form, tipo, precio_referencia)
- **Sucursal** (id, nombre, zona, ciudad)
- **Venta** (id, invoice, cliente_id, sucursal_id, fecha, total, metodo_pago, estado)
- **DetalleVenta** (id, venta_id, producto_id, cantidad, precio_unitario, subtotal)
- **Proveedor** (id, nombre, cuit, email, tiempo_entrega_dias)
- **OrdenCompra** (id, proveedor_id, sucursal_id, fecha_creacion, fecha_estimada, estado, motivo, total)
- **Inventario** (id, producto_id, sucursal_id, stock_actual, stock_minimo)
- **AsientoContable** (id, venta_id, caja_chica_id, tipo, monto, cuenta_debito, cuenta_credito, descripcion)
- **CajaChica** (id, sucursal_id, saldo_actual, saldo_minimo, estado)
- **MovimientoCaja** (id, caja_chica_id, tipo, monto, concepto, fecha)
- **AlertaDesercion** (id, cliente_id, dias_sin_compra, estado, accion_tomada)

**Relaciones:**

- Cliente (1) — (N) Venta
- Venta (1) — (N) DetalleVenta
- Producto (1) — (N) DetalleVenta
- Sucursal (1) — (N) Venta
- Producto (1) — (N) Inventario
- Sucursal (1) — (N) Inventario
- Proveedor (1) — (N) OrdenCompra
- Sucursal (1) — (N) OrdenCompra
- Venta (1) — (1) AsientoContable
- Sucursal (1) — (1) CajaChica
- CajaChica (1) — (N) MovimientoCaja
- Cliente (1) — (N) AlertaDesercion

**Notas:**
- Precio por linea se calcula como cantidad (Sales_Sheet) * precio_unitario desde tabla de precios.
- Cliente es sintetico y documentado como supuesto del proyecto.
- Stock por sucursal habilita reproceso multi-local.

---

*Documento generado por Firma Consultora INNOVATE TECH para el proyecto FarmaVida.*
