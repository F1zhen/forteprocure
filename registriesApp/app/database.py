from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Connects to the postgres service defined in docker-compose
# If running locally without docker networking, change 'db' to 'localhost'
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/zakup_registry"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()