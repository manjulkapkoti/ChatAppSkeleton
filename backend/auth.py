"""A minimal JWT mint/verify pair — a stand-in for whatever real auth system
your app already has. The chat pattern doesn't care how you authenticate;
it only cares that, by the time `require_user` or the WebSocket handshake
runs, you can hand it a verified `user_id` string.

If your app already issues JWTs, delete this file and point `chat_router.py`
at your own token-verification function instead — it only needs the same
shape: `str -> str | None` (token in, user id out, or `None` on failure).
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import jwt

# In real use: read from env, never hardcode. `main.py` sets a random one at
# startup (before this module is even imported) so the demo never actually
# runs on the literal fallback below — that fallback exists only so this file
# still works if it's ever imported standalone, outside main.py.
SECRET = os.environ.get("CHAT_DEMO_JWT_SECRET", "change-me")
ALGORITHM = "HS256"


def mint_token(user_id: str, expires_minutes: int = 60) -> str:
    now = datetime.now(UTC)
    payload = {"sub": user_id, "iat": now, "exp": now + timedelta(minutes=expires_minutes)}
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def verify_token(token: str) -> str | None:
    """Returns the user id, or None if the token is missing, expired, or
    tampered with. Never raises — every caller (HTTP and WebSocket alike)
    can treat `None` as "not authenticated" without a try/except of their own.
    """
    if not token:
        return None
    try:
        claims = jwt.decode(token, SECRET, algorithms=[ALGORITHM])  # pinned alg — rejects "none"/confusion attacks
    except jwt.PyJWTError:
        return None
    sub = claims.get("sub")
    return str(sub) if sub is not None else None
