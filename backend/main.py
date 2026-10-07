"""Wires the pattern into a runnable app. Run it:

    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000

Then, from a second terminal, try the demo flow (see README.md § Try it in
five minutes for the full walkthrough with two simulated users).

The `/demo/*` routes below exist ONLY because this reference has no
registration/login system of its own — delete them once you wire this into
an app that already issues its own JWTs and already knows who its users are.
Nothing under `/api` or `/ws` depends on them.
"""

from __future__ import annotations

import os
import secrets

# Must run BEFORE anything imports auth.py — its SECRET is read once, at
# import time, from this same env var. Filling it in here (only if the
# environment didn't already set one) means the demo signs tokens with a
# real random secret instead of quietly falling back to auth.py's literal
# "change-me". Restarting the server generates a new one and invalidates
# existing tokens — expected for a secret that was never meant to persist.
os.environ.setdefault("CHAT_DEMO_JWT_SECRET", secrets.token_hex(32))

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel
from sqlmodel import Session

import chat_router
from auth import mint_token
from db import engine, init_db
from models import Room


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    init_db()
    yield


app = FastAPI(title="WebSocket Chat Reference", lifespan=lifespan)
app.include_router(chat_router.router, prefix="/api")
app.include_router(chat_router.ws_router, prefix="/ws")


class TokenRequest(BaseModel):
    user_id: str


class RoomRequest(BaseModel):
    participant_a_id: str
    participant_b_id: str


@app.post("/demo/token")
def demo_mint_token(body: TokenRequest) -> dict:
    """Stand-in for "log in as this user." Returns a bearer token — use it as
    `Authorization: Bearer <token>` for REST, or `?token=<token>` for the
    WebSocket (see README.md)."""
    return {"access_token": mint_token(body.user_id)}


@app.post("/demo/rooms")
def demo_create_room(body: RoomRequest) -> dict:
    """Stand-in for whatever your app does to decide two users share a room."""
    with Session(engine) as session:
        room = Room(participant_a_id=body.participant_a_id, participant_b_id=body.participant_b_id)
        session.add(room)
        session.commit()
        session.refresh(room)
        return {"id": room.id}
