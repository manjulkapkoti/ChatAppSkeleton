"""A single SQLite file, zero setup. Swap `DATABASE_URL` for Postgres/MySQL/
whatever and nothing else in this reference changes — SQLModel's `Session`
API is the same either way."""

from __future__ import annotations

from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

DATABASE_URL = "sqlite:///./chat_reference.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
