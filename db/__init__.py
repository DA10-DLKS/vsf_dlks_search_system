from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
load_dotenv(_PROJECT_ROOT / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://da10:da10@localhost:5432/da10",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, class_=Session)


def create_tables() -> None:
    from db.models import Base
    Base.metadata.create_all(engine)


def drop_tables() -> None:
    from db.models import Base
    Base.metadata.drop_all(engine)
