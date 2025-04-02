# Copyright (c) 2024.
"""Utility functions for creating database connections."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from common.EnvManager import getenv

# try loading from .env file (only when running locally)
CONFIG = getenv()

DATABASE_URL = CONFIG["DB_URI"]

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()  # pyright: ignore[reportAny]


def get_db() -> Generator[Session, None, None]:
    """Provide a database session via a generator

    Yields:
        A database session generator

    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
