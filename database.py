import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./elp.db")
DATABASE_AUTH_TOKEN = os.environ.get("DATABASE_AUTH_TOKEN", "")

# Configure engine based on URL type
if DATABASE_URL.startswith("sqlite+libsql://"):
    # Connect to Turso Cloud (remote libSQL)
    url = DATABASE_URL
    if DATABASE_AUTH_TOKEN and "authToken=" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}authToken={DATABASE_AUTH_TOKEN}"
    engine = create_engine(url)
elif DATABASE_URL.startswith("sqlite://"):
    # Connect to local SQLite file
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # Handle other databases (e.g., PostgreSQL for future options)
    # If the URL uses the old 'postgres://' prefix, update to 'postgresql://' for SQLAlchemy
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

