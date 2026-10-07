"""THE ONE TRUST BOUNDARY. Every entry point in this pattern — the WebSocket
handshake (once, right after `accept()`) and every REST route — calls exactly
this function to decide "may this user act on this room." Nothing else in the
codebase re-implements the check.

Why that matters: a permission rule that lives in one place can only be wrong
in one place. A rule copy-pasted into three routes can drift into three
different, individually-plausible-looking bugs.

**This is the one file you're expected to rewrite for your own app.** The
example below (a room's two fixed participants, looked up in the DB) is
intentionally the simplest possible implementation — real apps plug in
whatever "is a member" means for them: a friends table, a project-members
table, a paid-access flag, an invite that hasn't expired, an org membership
role check. Whatever it is, keep it here, keep it a single function, and make
sure it's checked *live* (a fresh read, not a cached decision) every time —
that's what makes revocation work.
"""

from __future__ import annotations

from sqlmodel import Session

from models import Room


def is_member(session: Session, room: Room, user_id: str) -> bool:
    """Replace this body with your own app's membership rule. Keep the
    signature: (an already-loaded room, the caller's verified user id) -> bool.
    """
    return user_id in (room.participant_a_id, room.participant_b_id)
