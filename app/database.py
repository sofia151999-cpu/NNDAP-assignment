from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Hard drive
DATABASE_URL = "sqlite:///./farm.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False})  

# Session factory (access to BD)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine)

Base = declarative_base()