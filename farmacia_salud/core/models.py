"""Modelos del Core del sistema de farmacia.

Todas las entidades están en este módulo para evitar conflictos
de circularidad con SQLAlchemy.
"""

from sqlalchemy import (
    Column, Integer, String, Numeric, DateTime, ForeignKey, Date, Text
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class Sucursal(Base):
    __tablename__ = "sucursales"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), nullable=False, unique=True)
    zona = Column(String(20), nullable=False)
    ciudad = Column(String(50), nullable=False)
    direccion = Column(String(200))
    telefono = Column(String(50))
    activa = Column(Integer, default=1)

    inventarios = relationship("Inventario", back_populates="sucursal")
    cajas_chicas = relationship("CajaChica", back_populates="sucursal")
    ventas = relationship("Venta", back_populates="sucursal")


class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    barcode = Column(String(50), nullable=False, unique=True)
    nombre = Column(String(200), nullable=False)
    dosage_form = Column(String(50), nullable=False)
    tipo = Column(String(20), nullable=False)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=True)

    detalles_venta = relationship("DetalleVenta", back_populates="producto")
    inventarios = relationship("Inventario", back_populates="producto")
    proveedor_core = relationship("Proveedor", back_populates="productos")
    precio = relationship("Precio", uselist=False, back_populates="producto")


class Precio(Base):
    __tablename__ = "precios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), unique=True, nullable=False)
    precio_unitario = Column(Numeric(10, 2), nullable=False)
    moneda = Column(String(10), default="ARS")
    fecha_actualizacion = Column(DateTime, default=datetime.now)

    producto = relationship("Producto", back_populates="precio")


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String(50), unique=True, nullable=False)
    nombre = Column(String(150))
    email = Column(String(150))
    telefono = Column(String(50))
    fecha_primera_compra = Column(DateTime)
    fecha_ultima_compra = Column(DateTime)
    total_compras = Column(Numeric(12, 2), default=0)
    frecuencia = Column(Integer, default=0)
    segmento_rfm = Column(String(50), default="Nuevo")

    ventas = relationship("Venta", back_populates="cliente")


class Venta(Base):
    __tablename__ = "ventas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice = Column(String(50), nullable=False, unique=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), nullable=False)
    fecha = Column(DateTime, nullable=False, default=datetime.now)
    total = Column(Numeric(12, 2), nullable=False, default=0)
    metodo_pago = Column(String(50), default="Efectivo")
    estado = Column(String(20), default="Completada")

    cliente = relationship("Cliente", back_populates="ventas")
    sucursal = relationship("Sucursal", back_populates="ventas")
    detalles = relationship("DetalleVenta", back_populates="venta", cascade="all, delete-orphan")
    asientos = relationship("AsientoContable", back_populates="venta")


class DetalleVenta(Base):
    __tablename__ = "detalles_venta"

    id = Column(Integer, primary_key=True, autoincrement=True)
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)

    venta = relationship("Venta", back_populates="detalles")
    producto = relationship("Producto", back_populates="detalles_venta")


class Proveedor(Base):
    __tablename__ = "proveedores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(150), nullable=False)
    cuit = Column(String(20), unique=True)
    email = Column(String(150))
    telefono = Column(String(50))
    direccion = Column(String(200))
    tiempo_entrega_dias = Column(Integer, default=3)

    productos = relationship("Producto", back_populates="proveedor_core")
    ordenes_compra_core = relationship("ItemOrdenCompra", back_populates="proveedor")
    ordenes_compra = relationship("OrdenCompra", back_populates="proveedor")
    proveedores_scm = relationship("ProveedorSCM", back_populates="proveedor_core", uselist=False)


class OrdenCompra(Base):
    __tablename__ = "ordenes_compra"

    id = Column(Integer, primary_key=True, autoincrement=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=False)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), nullable=False)
    fecha_creacion = Column(DateTime, default=datetime.now)
    fecha_estimada = Column(DateTime)
    estado = Column(String(20), default="Pendiente")
    motivo = Column(String(300))
    total = Column(Numeric(12, 2), default=0)

    proveedor = relationship("Proveedor", back_populates="ordenes_compra")
    sucursal = relationship("Sucursal")
    items = relationship("ItemOrdenCompra", back_populates="orden_compra", cascade="all, delete-orphan")


class ItemOrdenCompra(Base):
    __tablename__ = "items_orden_compra"

    id = Column(Integer, primary_key=True, autoincrement=True)
    orden_compra_id = Column(Integer, ForeignKey("ordenes_compra.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)

    orden_compra = relationship("OrdenCompra", back_populates="items")
    proveedor = relationship("Proveedor", back_populates="ordenes_compra_core")
    producto = relationship("Producto")


class Inventario(Base):
    __tablename__ = "inventarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), nullable=False)
    stock_actual = Column(Integer, nullable=False, default=0)
    stock_minimo = Column(Integer, default=10)
    ubicacion = Column(String(100))
    ultima_entrada = Column(DateTime)
    ultima_salida = Column(DateTime)

    producto = relationship("Producto", back_populates="inventarios")
    sucursal = relationship("Sucursal", back_populates="inventarios")


class CajaChica(Base):
    __tablename__ = "cajas_chicas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), nullable=False, unique=True)
    saldo_actual = Column(Numeric(12, 2), nullable=False, default=0)
    saldo_minimo = Column(Numeric(12, 2), default=1000)
    moneda = Column(String(10), default="ARS")
    ultima_actualizacion = Column(DateTime, default=datetime.now)
    estado = Column(String(20), default="Abierta")

    sucursal = relationship("Sucursal", back_populates="cajas_chicas")
    movimientos = relationship("MovimientoCaja", back_populates="caja_chica")
    asientos = relationship("AsientoContable", back_populates="caja_chica")


class MovimientoCaja(Base):
    __tablename__ = "movimientos_caja"

    id = Column(Integer, primary_key=True, autoincrement=True)
    caja_chica_id = Column(Integer, ForeignKey("cajas_chicas.id"), nullable=False)
    tipo = Column(String(20), nullable=False)
    monto = Column(Numeric(12, 2), nullable=False)
    concepto = Column(String(200))
    fecha = Column(DateTime, default=datetime.now)
    asiento_id = Column(Integer, ForeignKey("asientos_contables.id"), nullable=True)

    caja_chica = relationship("CajaChica", back_populates="movimientos")
    asiento = relationship("AsientoContable", back_populates="movimientos")


class AsientoContable(Base):
    __tablename__ = "asientos_contables"

    id = Column(Integer, primary_key=True, autoincrement=True)
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=False, unique=True)
    caja_chica_id = Column(Integer, ForeignKey("cajas_chicas.id"), nullable=False)
    fecha = Column(DateTime, default=datetime.now)
    tipo = Column(String(20), nullable=False)
    monto = Column(Numeric(12, 2), nullable=False)
    cuenta_debito = Column(String(100), default="Caja / Bancos")
    cuenta_credito = Column(String(100), default="Ingresos por Ventas")
    descripcion = Column(Text)
    estado = Column(String(20), default="Registrado")

    venta = relationship("Venta", back_populates="asientos")
    caja_chica = relationship("CajaChica", back_populates="asientos")
    movimientos = relationship("MovimientoCaja", back_populates="asiento")


class AlertaDesercion(Base):
    __tablename__ = "alertas_desercion"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    fecha_deteccion = Column(DateTime, default=datetime.now)
    dias_sin_compra = Column(Integer, nullable=False)
    estado = Column(String(20), default="En riesgo")
    accion_tomada = Column(String(200))
    observaciones = Column(Text)


class ProveedorSCM(Base):
    __tablename__ = "proveedores_scm"

    id = Column(Integer, primary_key=True, autoincrement=True)
    proveedor_core_id = Column(Integer, ForeignKey("proveedores.id"), unique=True)
    nombre = Column(String(150), nullable=False)
    cuit = Column(String(20), unique=True)
    email = Column(String(150))
    telefono = Column(String(50))
    direccion = Column(String(200))
    tiempo_entrega_dias = Column(Integer, default=3)
    activo = Column(Integer, default=1)

    proveedor_core = relationship("Proveedor")
    ordenes_compra = relationship("OrdenCompraSCM", back_populates="proveedor")


class OrdenCompraSCM(Base):
    __tablename__ = "ordenes_compra_scm"

    id = Column(Integer, primary_key=True, autoincrement=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores_scm.id"), nullable=False)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), nullable=False)
    fecha_creacion = Column(DateTime, default=datetime.now)
    fecha_estimada = Column(DateTime)
    estado = Column(String(20), default="Pendiente")
    motivo = Column(String(300))
    total = Column(Numeric(12, 2), default=0)

    proveedor = relationship("ProveedorSCM", back_populates="ordenes_compra")
    sucursal = relationship("Sucursal")
    items = relationship("ItemOrdenCompraSCM", back_populates="orden_compra", cascade="all, delete-orphan")


class ItemOrdenCompraSCM(Base):
    __tablename__ = "items_orden_compra_scm"

    id = Column(Integer, primary_key=True, autoincrement=True)
    orden_compra_id = Column(Integer, ForeignKey("ordenes_compra_scm.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    proveedor_id = Column(Integer, ForeignKey("proveedores_scm.id"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)

    orden_compra = relationship("OrdenCompraSCM", back_populates="items")
    proveedor = relationship("ProveedorSCM")
    producto = relationship("Producto")


class InventarioSCM(Base):
    __tablename__ = "inventarios_scm"

    id = Column(Integer, primary_key=True, autoincrement=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), nullable=False)
    stock_actual = Column(Integer, nullable=False, default=0)
    stock_minimo = Column(Integer, default=10)
    ubicacion = Column(String(100))
    ultima_entrada = Column(DateTime)
    ultima_salida = Column(DateTime)

    producto = relationship("Producto")
    sucursal = relationship("Sucursal")
