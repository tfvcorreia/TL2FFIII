from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for FastAPI routes"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(bind=None):
    """Initialize database tables"""
    database_engine = bind or engine
    Base.metadata.create_all(bind=database_engine)

    columns = {
        column["name"]
        for column in inspect(database_engine).get_columns("imported_transactions")
    }
    if "transaction_details" not in columns:
        with database_engine.begin() as connection:
            connection.execute(text(
                "ALTER TABLE imported_transactions ADD COLUMN transaction_details JSON"
            ))
