"""Response shapes. Kept separate from `models.py` on purpose: a DB table and
an API response are different contracts, and a field you add to one should
never silently appear on the other. (In this reference there's nothing
private to hide — but in a real app, this is exactly the seam where you'd
keep an internal field off the wire.)
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class RoomSummary(BaseModel):
    id: int
    counterpart_id: str
    unread_count: int


class MessageOut(BaseModel):
    id: int
    room_id: int
    sender_id: str
    text: str
    created_at: datetime
