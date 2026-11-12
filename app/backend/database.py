import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session

load_dotenv(Path(__file__).with_name(".env"))

engine = create_engine(
    os.environ["DATABASE_URL"],
    pool_pre_ping=True,
)

class Base(DeclarativeBase):
    pass

def get_db():
    with Session(engine) as session:
        yield session