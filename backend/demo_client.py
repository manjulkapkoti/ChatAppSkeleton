"""An interactive two-terminal demo client — talks to the running `main.py`
server over plain HTTP + WebSocket, no browser needed. Not part of the
pattern itself (just a way to see it work); safe to delete.

Usage:

    # one-time setup: mints tokens for two demo users and creates a room
    python demo_client.py setup alice bob

    # then, in TWO separate terminals, paste the two printed commands —
    # each opens a live connection you can type into and see the other
    # side's messages arrive in real time.
    python demo_client.py chat "<token>" <room_id> alice
    python demo_client.py chat "<token>" <room_id> bob
"""

from __future__ import annotations

import json
import os
import sys
import threading
import urllib.request

# Override with CHAT_DEMO_BASE_URL if you're running the server on a
# different port (e.g. because 8000 is already in use by something else).
BASE = os.environ.get("CHAT_DEMO_BASE_URL", "http://localhost:8000")
WS_BASE = BASE.replace("http://", "ws://").replace("https://", "wss://")


def post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def setup(user_a: str, user_b: str) -> None:
    token_a = post("/demo/token", {"user_id": user_a})["access_token"]
    token_b = post("/demo/token", {"user_id": user_b})["access_token"]
    room_id = post("/demo/rooms", {"participant_a_id": user_a, "participant_b_id": user_b})["id"]

    print(f"\nRoom id: {room_id}\n")
    print("Paste each of these into its own terminal:\n")
    print(f'python demo_client.py chat "{token_a}" {room_id} {user_a}\n')
    print(f'python demo_client.py chat "{token_b}" {room_id} {user_b}\n')


def chat(token: str, room_id: int, name: str) -> None:
    from websockets.sync.client import connect

    url = f"{WS_BASE}/ws/rooms/{room_id}?token={token}"
    with connect(url) as ws:
        print(f"Connected as {name}. Type a message and press enter (Ctrl+C to quit).\n")

        def receiver() -> None:
            while True:
                try:
                    raw = ws.recv()
                except Exception:
                    break
                frame = json.loads(raw)
                if frame.get("type") == "message":
                    who = "you" if frame["sender_id"] == name else frame["sender_id"]
                    print(f"\n[{who}] {frame['text']}\n> ", end="", flush=True)
                elif frame.get("type") == "error":
                    print(f"\n[error] {frame['code']}\n> ", end="", flush=True)

        threading.Thread(target=receiver, daemon=True).start()

        try:
            while True:
                text = input("> ")
                if text.strip():
                    ws.send(json.dumps({"text": text}))
        except (KeyboardInterrupt, EOFError):
            print("\nDisconnecting…")
            # falling out of the `with connect(...)` block below sends a
            # proper close frame before the process exits.


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "setup":
        setup(sys.argv[2], sys.argv[3])
    elif len(sys.argv) >= 5 and sys.argv[1] == "chat":
        chat(sys.argv[2], int(sys.argv[3]), sys.argv[4])
    else:
        print(__doc__)
