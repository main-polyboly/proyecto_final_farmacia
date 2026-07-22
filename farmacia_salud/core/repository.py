"""Repositorio SQLAlchemy para acceso a datos."""

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from core.models import Base
import os

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "farmacia.db")
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db(drop=False):
    if drop and os.path.exists(DATABASE_PATH):
        engine.dispose()
        os.remove(DATABASE_PATH)
    Base.metadata.create_all(engine)


def get_session():
    return SessionLocal()
