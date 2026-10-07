"""The WebSocket handshake, the message loop, and the three REST reads.

Read this file top to bottom once — it's the whole pattern in ~150 lines.
Every design decision here is explained where it happens, not in a separate
doc, because the reason usually only makes sense next to the three lines of
code it's protecting.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlmodel import Session, func, or_, select

from auth import verify_token
from chat_broker import chat_broker
from db import get_session
from membership import is_member
from models import Message, Room, utcnow
from rate_limiter import InMemoryRateLimiterBackend, RateLimiter
from schemas import MessageOut, RoomSummary

router = APIRouter()
ws_router = APIRouter()

# Per-(room, user) message cap. In-process — see rate_limiter.py's own
# docstring for the horizontal-scale caveat.
_chat_rate_limiter = RateLimiter(max_attempts=20, window_seconds=10, backend=InMemoryRateLimiterBackend())

HISTORY_PAGE_LIMIT = 50


# ── Auth for REST (the WS handshake below authenticates itself differently —
#    a browser can't attach a custom header to a WebSocket handshake, so the
#    token has to travel as a query param there instead) ────────────────────


def require_user(authorization: str = Header(default="")) -> str:
    token = authorization.removeprefix("Bearer ").strip()
    user_id = verify_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_id


def require_membership(
    room_id: int, user_id: str = Depends(require_user), session: Session = Depends(get_session)
) -> Room:
    """The REST wrapper around `is_member` (membership.py) — the same trust
    boundary the WebSocket handshake uses, re-checked on every single call.
    A room that doesn't exist and a room you're not in return the *same*
    error, so probing ids never tells an attacker which is which."""
    room = session.get(Room, room_id)
    if room is not None and is_member(session, room, user_id):
        return room
    raise HTTPException(status_code=403, detail="Not a member of this room")


# ── The WebSocket handshake + message loop ───────────────────────────────────


@ws_router.websocket("/rooms/{room_id}")
async def room_socket(
    websocket: WebSocket,
    room_id: int,
    token: str = Query(default=""),
    session: Session = Depends(get_session),
) -> None:
    """Connect, authenticate, and hold one room's live socket.

    THE ORDER OF THESE STEPS IS THE SECURITY PROPERTY. Read it as a sequence,
    not a bag of checks:

      1. accept() — the ONLY real await/yield point in this whole flow, and
         it comes FIRST, before anything else runs.
      2. Authenticate the token (sync — no further yield point).
                                                 -> fail: close(4001)
      3. Check membership (sync — no further yield point).
                                                 -> fail: close(4003)
      4. Register the socket with the broker.

    Why accept() has to come first, not last: a real ASGI server (uvicorn)
    that never sees `websocket.accept()` rejects the HTTP upgrade itself and
    reports a bare `HTTP 403` to the client — the specific close code
    (4001/4003) you gave `websocket.close()` is silently discarded, because
    the WebSocket protocol was never established for a close frame to carry
    it over. This is invisible if you only test against Starlette's
    in-process `TestClient` (which *does* faithfully preserve a pre-accept
    close code) and only shows up against a real server + a real client —
    exactly the inverse of this reference's other testing gotcha (a test
    double being *too* permissive instead of too strict). Accepting first
    means the close frame that follows travels over an established
    connection, and the client's WebSocket library actually sees the code.

    This ordering also removes a step the previous design needed: because
    `accept()` is now the ONLY yield point and it happens BEFORE steps 2-3
    instead of between two checks, nothing can change this user's access
    between "check membership" and "register" — there's no `await` in
    between for anything else to run during. One membership check, right
    after accept(), is enough; a second post-register re-check would only
    ever re-confirm what the first one already found.
    """
    await websocket.accept()

    user_id = verify_token(token)
    if user_id is None:
        await websocket.close(code=4001, reason="auth_failed")
        return

    room = session.get(Room, room_id)
    if room is None or not is_member(session, room, user_id):
        await websocket.close(code=4003, reason="not_a_member")
        return

    chat_broker.register(room_id, user_id, websocket)
    limiter_key = f"{room_id}:{user_id}"

    try:
        while True:
            try:
                raw = await websocket.receive_text()
            except WebSocketDisconnect:
                break

            # Rate-limit BEFORE parsing/validating content. Checking the cap
            # only for messages that already passed validation means a flood
            # of garbage/oversized frames never spends any budget — the cap
            # would exist and do nothing. Every inbound frame counts, valid
            # or not.
            if not _chat_rate_limiter.check(limiter_key):
                await websocket.close(code=4009, reason="rate_limited")
                return

            try:
                data = json.loads(raw)
                text = data.get("text") if isinstance(data, dict) else None
            except (json.JSONDecodeError, AttributeError):
                text = None

            if not isinstance(text, str) or not text.strip():
                await websocket.send_json({"type": "error", "code": "invalid_message"})
                continue
            if len(text) > 4000:
                await websocket.send_json({"type": "error", "code": "message_too_long"})
                continue

            message = Message(room_id=room_id, sender_id=user_id, text=text.strip())
            session.add(message)
            session.commit()
            session.refresh(message)

            # Broadcast to EVERY registered socket in this room, sender
            # included — see chat_broker.py's `publish()` docstring for why.
            # sender_id here is `user_id`, the value THIS handshake verified —
            # never anything read out of `data`. A payload claiming to be
            # someone else is simply never looked at.
            await chat_broker.publish(
                room_id,
                {
                    "type": "message",
                    "id": message.id,
                    "room_id": room_id,
                    "sender_id": user_id,
                    "text": message.text,
                    "created_at": message.created_at.isoformat(),
                },
            )
    finally:
        chat_broker.unregister(room_id, user_id, websocket)


# ── REST: list rooms, read history, mark read ────────────────────────────────


@router.get("/rooms", response_model=list[RoomSummary])
def list_rooms(user_id: str = Depends(require_user), session: Session = Depends(get_session)) -> list[RoomSummary]:
    """Every room the caller belongs to — scoped in the query itself (the
    WHERE clause), not filtered after loading everything. That's what makes
    this caller-scoped rather than merely caller-filtered: another user's
    room is never even fetched, so there's nothing a serialization bug could
    leak."""
    rooms = session.exec(
        select(Room).where(or_(Room.participant_a_id == user_id, Room.participant_b_id == user_id))
    ).all()

    summaries: list[RoomSummary] = []
    for room in rooms:
        is_a = room.participant_a_id == user_id
        counterpart_id = room.participant_b_id if is_a else room.participant_a_id
        last_read = room.a_last_read_at if is_a else room.b_last_read_at

        unread_query = select(func.count()).select_from(Message).where(
            Message.room_id == room.id, Message.sender_id != user_id
        )
        if last_read is not None:
            unread_query = unread_query.where(Message.created_at > last_read)
        unread_count = session.exec(unread_query).one()

        summaries.append(RoomSummary(id=room.id, counterpart_id=counterpart_id, unread_count=unread_count))
    return summaries


@router.get("/rooms/{room_id}/messages", response_model=list[MessageOut])
def get_room_messages(
    room: Room = Depends(require_membership),
    before: int | None = None,
    limit: int = Query(default=HISTORY_PAGE_LIMIT, ge=1, le=HISTORY_PAGE_LIMIT),
    session: Session = Depends(get_session),
) -> list[Message]:
    """Newest page first; pass `before=<message id>` to page further back.
    `limit`'s ceiling is enforced by the schema (a 422 if you ask for more),
    not silently clamped — a silent clamp hides the ceiling from whoever
    hits it."""
    query = select(Message).where(Message.room_id == room.id)
    if before is not None:
        query = query.where(Message.id < before)
    query = query.order_by(Message.id.desc()).limit(limit)
    return session.exec(query).all()


@router.post("/rooms/{room_id}/read", status_code=204)
def mark_room_read(
    room: Room = Depends(require_membership),
    user_id: str = Depends(require_user),
    session: Session = Depends(get_session),
) -> None:
    """Stamp the caller's own `*_last_read_at`. `require_membership` already
    proved the caller is one of the room's two participants, so no second
    lookup is needed to know which column is theirs."""
    if user_id == room.participant_a_id:
        room.a_last_read_at = utcnow()
    else:
        room.b_last_read_at = utcnow()
    session.add(room)
    session.commit()
