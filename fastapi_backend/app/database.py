import os
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker, declarative_base
# Load values from the .env file
load_dotenv()


# Get database details from .env
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "smart_ecommerce")
DB_PASSWORD = os.getenv("DB_PASSWORD", "smart_ecommerce")
DB_NAME = os.getenv("DB_NAME", "smart_ecommerce")


DATABASE_URL = os.getenv("DATABASE_URL") or URL.create(
    drivername="mysql+pymysql",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=int(DB_PORT),
    database=DB_NAME
)

# Create database engine
engine_options = {"pool_pre_ping": True}
if str(DATABASE_URL).startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, **engine_options)


# Create database session
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine)


# Base class for SQLAlchemy models
Base = declarative_base()


@event.listens_for(Base, "before_insert", propagate=True)
def set_insert_timestamps(mapper, connection, target):
    """Supply timestamps because Django migrations own columns without DB defaults."""
    now = datetime.utcnow()
    if hasattr(target, "created_at") and getattr(target, "created_at", None) is None:
        target.created_at = now
    if hasattr(target, "updated_at") and getattr(target, "updated_at", None) is None:
        target.updated_at = now


@event.listens_for(Base, "before_update", propagate=True)
def set_update_timestamp(mapper, connection, target):
    if hasattr(target, "updated_at"):
        target.updated_at = datetime.utcnow()


# Function to get database connection
def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
