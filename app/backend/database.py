import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session

load_dotenv(Path(__file__).with_name(".env"))

database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise RuntimeError(
        "DATABASE_URL is required. Set it to the connection URL of your PostgreSQL database."
    )

# Render may supply `postgres://` or `postgresql://`; explicitly select the
# psycopg 3 driver installed by requirements.txt.
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(
    database_url,
    pool_pre_ping=True,
)

class Base(DeclarativeBase):
    pass

def get_db():
    with Session(engine) as session:
        yield session