from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base

engine = create_engine('sqlite:///transactions.db') 

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()