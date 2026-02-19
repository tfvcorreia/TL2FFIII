from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

def get_engine():
    return create_engine(app.config['DATABASE_URL'])

Session = sessionmaker(bind=get_engine())

# Example Model
class ExampleModel(Base):
    __tablename__ = 'example'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

# Initialize Database
if __name__ == '__main__':
    Base.metadata.create_all(get_engine())