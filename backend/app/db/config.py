import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# PostgreSQL PostGIS default connection string; falls back to SQLite for environments without active local Postgres
DEFAULT_PG_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1215@localhost:5432/transportation_db")
DATABASE_URL = DEFAULT_PG_URL

USE_POSTGRES = False

def create_db_engine():
    global USE_POSTGRES
    env_url = os.getenv("DATABASE_URL")
    candidate_urls = [env_url] if env_url else [
        "postgresql://postgres:1215@localhost:5432/transportation_db",
        "postgresql://postgres:postgres@localhost:5432/transportation_db"
    ]
    
    for url in candidate_urls:
        if url and url.startswith("postgresql"):
            try:
                eng = create_engine(url, pool_pre_ping=True)
                with eng.connect():
                    pass
                USE_POSTGRES = True
                print(f"Connected to PostgreSQL database: {url}")
                return eng
            except Exception as e:
                print(f"PostgreSQL connection to {url} failed: {e}")
    
    # Fallback to SQLite if PostgreSQL is completely offline
    sqlite_url = "sqlite:///./transportation.db"
    eng = create_engine(sqlite_url, connect_args={"check_same_thread": False})
    USE_POSTGRES = False
    print(f"Using SQLite database: {sqlite_url}")
    return eng

engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
