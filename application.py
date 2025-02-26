from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import mysql.connector
import pandas as pd
import joblib

app = FastAPI()

# Configuración de la base de datos MySQL
DATABASE_URL = "mysql+mysqlconnector://wsuarez:Afsmnz78@mi-backend-aqaxd3g5a2h5azgp.spaincentral-01.azurewebsites.net/ventas_bd"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Modelos de Base de Datos
class Cliente(Base):
    __tablename__ = "clientes"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), unique=True, index=True)
    credito_disponible = Column(Float)

class Venta(Base):
    __tablename__ = "ventas"
    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"))
    monto = Column(Float)
    categoria = Column(String(50))
    ciudad = Column(String(50))
    cliente = relationship("Cliente")

class Cobranza(Base):
    __tablename__ = "cobranzas"
    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"))
    monto_pagado = Column(Float)
    cliente = relationship("Cliente")

# Crear tablas
Base.metadata.create_all(bind=engine)

# Modelo de entrada para consultas
class ClienteConsulta(BaseModel):
    nombre: str

# Cargar modelo de IA
modelo_ventas = joblib.load("modelo_ventas.pkl")

@app.get("/productos_mas_vendidos/")
def productos_mas_vendidos():
    db = SessionLocal()
    ventas = db.query(Venta.categoria).all()
    df = pd.DataFrame(ventas, columns=["categoria"])
    return df["categoria"].value_counts().to_dict()

@app.post("/evaluar_cliente/")
def evaluar_cliente(datos: ClienteConsulta):
    db = SessionLocal()
    cliente = db.query(Cliente).filter(Cliente.nombre == datos.nombre).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    total_compras = db.query(Venta).filter(Venta.cliente_id == cliente.id).sum(Venta.monto)
    total_cobrado = db.query(Cobranza).filter(Cobranza.cliente_id == cliente.id).sum(Cobranza.monto_pagado)
    saldo = total_compras - total_cobrado
    
    prediccion = modelo_ventas.predict([[total_compras, total_cobrado, cliente.credito_disponible]])
    
    return {
        "nombre": cliente.nombre,
        "total_compras": total_compras,
        "total_cobrado": total_cobrado,
        "saldo_pendiente": saldo,
        "credito_disponible": cliente.credito_disponible,
        "puede_comprar": bool(prediccion[0])
    }
