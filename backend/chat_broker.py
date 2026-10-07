"""Fan-out, behind a swappable port.

The in-process registry below is the correct choice for a single server
process. The moment you run more than one process (multiple containers, a
serverless-per-request model, anything horizontally scaled), a sender on
process A and a recipient connected to process B will never see each other's
messages — silently. No error, just a broken product.

The fix is not "don't use this pattern" — it's "swap the implementation."
Everything that talks to `chat_broker` only ever calls `register` /
`unregister` / `publish` / `close_user`. Replace `InMemoryChatBroker` with one
backed by Redis pub/sub, NATS, or Postgres `LISTEN/NOTIFY`, and nothing that
calls it has to change.
"""

from __future__ import annotations

from typing import Protocol

from fastapi import WebSocket


class ChatBroker(Protocol):
    def register(self, room_id: int, user_id: str, websocket: WebSocket) -> None: ...
    def unregister(self, room_id: int, user_id: str, websocket: WebSocket) -> None: ...
    async def publish(self, room_id: int, payload: dict) -> None: ...
    async def close_user(self, room_id: int, user_id: str, code: int, reason: str) -> None: ...


class InMemoryChatBroker:
    """`{room_id: {user_id: {sockets}}}`. A user can have more than one open
    socket (multiple tabs/devices) — all of them get every message."""

    def __init__(self) -> None:
        self._sockets: dict[int, dict[str, set[WebSocket]]] = {}

    def register(self, room_id: int, user_id: str, websocket: WebSocket) -> None:
        self._sockets.setdefault(room_id, {}).setdefault(user_id, set()).add(websocket)

    def unregister(self, room_id: int, user_id: str, websocket: WebSocket) -> None:
        users = self._sockets.get(room_id)
        if not users:
            return
        sockets = users.get(user_id)
        if sockets:
            sockets.discard(websocket)
            if not sockets:
                users.pop(user_id, None)
        if not users:
            self._sockets.pop(room_id, None)

    async def publish(self, room_id: int, payload: dict) -> None:
        """Fan out to every registered socket in this room — the sender's own
        socket included. That's deliberate: it means the client never has a
        separate "did my message send" code path. One code path renders
        every message, whoever sent it, once the server confirms it."""
        users = self._sockets.get(room_id, {})
        for sockets in list(users.values()):
            for websocket in list(sockets):
                try:
                    await websocket.send_json(payload)
                except Exception:
                    pass  # a dead socket gets cleaned up by its own disconnect handler

    async def close_user(self, room_id: int, user_id: str, code: int, reason: str) -> None:
        """Force-close every live socket a user has open in this room. This
        is what makes revocation *immediate*: when your app decides someone
        no longer belongs in a room, call this — don't wait for their next
        message or reconnect to find out."""
        sockets = self._sockets.get(room_id, {}).get(user_id, set())
        for websocket in list(sockets):
            try:
                await websocket.close(code=code, reason=reason)
            except Exception:
                pass


chat_broker: ChatBroker = InMemoryChatBroker()
