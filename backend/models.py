"""The two tables this pattern needs. Swap the ORM/DB freely — nothing else
in this reference depends on SQLModel specifically, only `db.py` does.

`Room` is deliberately storage-agnostic about *why* two users share a room —
that's your app's business logic (a support ticket, a DM, a purchase
inquiry...). This pattern only cares that a room has an id and, optionally,
a per-participant "last read" marker for unread counts.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC)


class Room(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    # Swap this for however *your* app decides who's in a room — a foreign
    # key to a support ticket, a project, a DM pair, a purchase inquiry...
    # This reference keeps it simple: two fixed participant ids.
    participant_a_id: str = Field(index=True)
    participant_b_id: str = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow)
    # Per-participant "last read" — the unread-count mechanism (see chat_router.py).
    a_last_read_at: datetime | None = None
    b_last_read_at: datetime | None = None


class Message(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    room_id: int = Field(foreign_key="room.id", index=True)
    # ALWAYS the verified connection's user id — never trust this from the
    # message payload. See chat_router.py's handshake for why.
    sender_id: str
    text: str
    created_at: datetime = Field(default_factory=utcnow)
