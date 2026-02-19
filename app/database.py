from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.dependency import Session
from sqlalchemy.orm import sessionmaker

# Load settings from app.config
def get_config():
    # This should return your database URL from the config
    return "sqlite:///./test.db"  # Example config, adjust accordingly

SQLALCHEMY_DATABASE_URL = get_config()

# SQLAlchemy base class
Base = declarative_base()

# SQLAlchemy session
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Init database function to create tables
def init_db():
    # Import your models here to register them with Base
    from . import models  # adjust based on your models' path
    Base.metadata.create_all(bind=engine)