import SQLAlchemy
from app.config import settings

def get_db():
    db = SQLAlchemy()
    # Assuming use of the settings.database_url for database connection
    db.init_app(settings.database_url)
    return db

def init_db():
    # Logic to initialize the database would go here
    pass
