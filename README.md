# WebSocket Chat — a Reusable Architecture

A small, framework-agnostic reference implementation of realtime chat over a
WebSocket: authentication at the handshake, membership re-checked _live_ (not
cached), a shared trust boundary, and a swappable fan-out layer. Extracted and
generalized from a production build, with every hard-won lesson kept in.

**New to WebSockets?** Start with
[`diagram/websocket_primer.html`](diagram/websocket_primer.html) — a
five-minute, jargon-free primer that follows one running example (Alice, Bob,
Priya, and Mallory in a shared room) through the trust boundary and fan-out,
before you hit either term in the architecture diagram below.

**Architecture diagram:** [`diagram/websocket_chat_architecture.html`](diagram/websocket_chat_architecture.html)
(open directly in a browser, works offline) — a legend, a "why + file" line on
every box, and a **role/responsibility appendix at the bottom of the page**
(same box, more room to explain it) — editable source at
[`diagram/websocket_chat_architecture.excalidraw`](diagram/websocket_chat_architecture.excalidraw)
(open at [excalidraw.com](https://excalidraw.com) → File → Open, or drag the
file in).

`diagram/elements_websocket_chat.json` is the single source of truth for all
of it — including the appendix, generated from each box's `role` field, not
hand-written. If you edit the JSON, regenerate all three outputs, in order,
from the repo root:

```bash
node docs/diagrams/diagGenerator/convert.js websocket-chat-reference/diagram/elements_websocket_chat.json websocket-chat-reference/diagram/websocket_chat_architecture.excalidraw 5
node docs/diagrams/diagGenerator/svg_gen.js websocket-chat-reference/diagram/elements_websocket_chat.json websocket-chat-reference/diagram/websocket_chat_architecture.html "WebSocket Chat — Reusable Architecture" "40 -10 1160 1280" "Shantell Sans"
node websocket-chat-reference/diagram/gen_role_appendix.js websocket-chat-reference/diagram/elements_websocket_chat.json websocket-chat-reference/diagram/websocket_chat_architecture.html
```

The third command must run _after_ `svg_gen.js` — it injects the appendix
into the HTML `svg_gen.js` just wrote; running it first would have nothing to
inject into. It's idempotent (safe to re-run), and only touches the appendix
section, not the diagram itself.

**Building a non-web client (e.g. a C++ desktop app)?** The backend doesn't
care what language its client speaks — WebSocket is a wire protocol, not a
browser feature.
[`diagram/websocket_cpp_client_mapping.html`](diagram/websocket_cpp_client_mapping.html)
maps every concept in `chatStore.ts` (the handshake, close codes, message
frames, REST reads, the store/lifecycle object) onto its C++ equivalent,
plus the one thing that doesn't map 1:1 (threading) and a couple of concrete
library starting points.

```
websocket-chat-reference/
├── README.md                    ← you are here
├── diagram/
│   ├── websocket_primer.html            ← start here if WebSockets are new to you
│   ├── websocket_chat_architecture.html ★ the diagram + role appendix — the main reference
│   ├── websocket_chat_architecture.excalidraw   editable source (excalidraw.com)
│   ├── websocket_cpp_client_mapping.html  Python/TS → C++ concept mapping, for non-web clients
│   ├── elements_websocket_chat.json     the single source of truth for the architecture diagram + appendix
│   └── gen_role_appendix.js             generates the appendix from the JSON's `role` fields
├── backend/                     ← FastAPI reference implementation (Python)
│   ├── models.py                Room, Message — the only two tables this needs
│   ├── membership.py            THE ONE TRUST BOUNDARY — rewrite this for your app
│   ├── chat_broker.py           fan-out, behind a swappable port
│   ├── rate_limiter.py          the message-rate cap
│   ├── auth.py                  a minimal JWT stand-in — delete if you have your own
│   ├── db.py                    a single SQLite file, zero setup
│   ├── schemas.py                REST response shapes
│   ├── chat_router.py           ★ the WS handshake + message loop + REST reads — read this file
│   ├── main.py                  wires it into a runnable app + two /demo/* helper routes
│   └── demo_client.py           an interactive two-terminal client — see "Try it" below
└── frontend/                    ← TypeScript reference implementation
    ├── chatStore.ts             ★ the WebSocket lifecycle, framework-agnostic
    ├── useChatStore.ts           the React adapter (useSyncExternalStore, no extra library)
    ├── ChatWindow.tsx            example UI: history + live messages
    ├── RoomList.tsx              example UI: the room list + unread badges
    └── App.example.tsx           how the pieces wire together (not meant to be copied verbatim)
```

## Try it in five minutes

**Terminal 1 — start the server:**

```bash
cd backend
python -m venv .venv
```

Activate it:

- **PowerShell (Windows):** `.\.venv\Scripts\Activate.ps1`. If PowerShell
  refuses to run the script, run this once:
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
- **cmd (Windows):** `.venv\Scripts\activate.bat`
- **macOS/Linux:** `source .venv/bin/activate`

Then:

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Use a virtual environment, not your system Python.** Installing straight
into a global/system install can fail on Windows with something like
`Could not install packages due to an OSError: ... 'uvicorn.exe.deleteme'`
(or any other `<name>.exe.deleteme`)
— pip trying to replace a console script that's currently locked by another
process using that same global install. A fresh venv has no such file to
conflict with, and it's the right way to install this regardless.

**If port 8000 is already in use** (a common symptom: `demo_client.py setup`
fails with `HTTPError: HTTP Error 404: Not Found` on `/demo/token` — not a
connection error, an actual 404, because _something else_ answered on that
port and it isn't this server), run on a different port instead:

Terminal 1:

```bash
uvicorn main:app --reload --port 8123
```

Terminals 2/3/4 — set `CHAT_DEMO_BASE_URL` in **every** terminal you use for
this, before running `demo_client.py`:

```powershell
$env:CHAT_DEMO_BASE_URL="http://localhost:8123"    # PowerShell
```

```cmd
set CHAT_DEMO_BASE_URL=http://localhost:8123  # cmd
```

```bash
export CHAT_DEMO_BASE_URL="http://localhost:8123"  # bash/zsh
```

Terminal 1 itself will usually tell you outright if the port was taken —
look for `error while attempting to bind on address` or "address already in
use" in its output.

**Terminal 2 — set up two demo users and a room:**

Open a **second terminal**, leaving the server running in the first. `cd`
into the same `backend/` folder and activate the same venv there too —
`setup` itself only uses Python's stdlib, but `chat` (next) needs the
`websockets` package from that venv, so just activate it in every terminal
you use for this:

```bash
cd backend
.\.venv\Scripts\Activate.ps1    # PowerShell · cmd: .venv\Scripts\activate.bat · macOS/Linux: source .venv/bin/activate
python demo_client.py setup alice bob
```

This prints two ready-to-paste commands, each carrying a token for one user,
and the id of a new room. Each run of `setup` creates another room.

The tokens are tied to the running server. If you restart the server (with
`--reload`, that happens on every code save), run `setup` again to get fresh
tokens. Old ones are rejected when you connect.

**Terminals 3 and 4 — paste one command into each:**

Same deal — `backend/` folder, venv activated, in two more separate
terminals:

```bash
python demo_client.py chat "<alice's token>" <room id> alice
python demo_client.py chat "<bob's token>" <room id> bob
```

Type in either terminal and press enter — the message appears in both, live.

**To quit a `chat` client:** press **Ctrl+C** — it prints "Disconnecting…"
and closes the WebSocket with a proper close frame before exiting. Just
closing the terminal window works too (Windows kills the attached process
along with it), but Ctrl+C is the clean way. Either way, the server cleans
up its side of the connection regardless of how the client went away, so
nothing lingers server-side. Reconnect any time with the same command — the
message history is still there.

`demo_client.py` exists only to make the WebSocket half easy to poke at from
a terminal — it isn't part of the pattern itself, and it's safe to delete.
For the REST half, `http://localhost:8000/docs` has interactive docs for
`/api/rooms`, history, and mark-read (WebSocket routes don't show up there —
OpenAPI doesn't cover them, which is exactly why the terminals above are
worth doing once).

## The architecture, in order

The diagram lays this out visually; this is the same walk in prose.

**1. The WebSocket handshake (once per connection) — order is the security property:**

1. **`accept()`** — the only real `await`/yield point in the whole handshake, and it comes **first**, before any check.
2. **Authenticate** the token (sync — no further yield point). Invalid/missing/expired → `close(4001)`.
3. **Check membership** (sync — no further yield point): `is_member(room, user_id)`. Not a member → `close(4003)`.
4. **Register** the socket with the broker.

`accept()` has to come first, not last, and this ordering is the result of a
real bug, not a design taste: a real ASGI server (uvicorn) that never sees
`websocket.accept()` rejects the HTTP upgrade itself and reports a bare
`HTTP 403` to the client — the specific close code you gave `websocket.close()`
is silently discarded, because the WebSocket protocol was never established
for a close frame to carry it over. **This is invisible against Starlette's
in-process `TestClient`**, which faithfully preserves a pre-accept close
code, and only shows up against a real server + a real client — the exact
inverse of the other testing gotcha below (a test double being _too_
permissive instead of too strict). An earlier version of this reference
checked auth and membership _before_ `accept()`, passed every `TestClient`
test, and still produced `websockets.exceptions.InvalidStatus: ... HTTP 403`
for every real client — reproduced with a real `uvicorn` process and the
`websockets` library before being fixed to the order above.

Accepting first also **removes a step** the earlier version needed: because
`accept()` is now the only yield point and it happens _before_ the checks
instead of _between_ two of them, nothing can change this user's access
between "check membership" and "register" — there's no `await` in between
for anything else to run during. One membership check, right after
`accept()`, is enough; a second post-register re-check would only ever
re-confirm what the first one already found.

**2. The message loop (per received frame), in this order:**

1. **Rate-limit check FIRST.**
2. **Validate content** (non-fatal — send an error frame, stay connected).
3. **Persist.**
4. **`broker.publish()`** — every member's socket, sender's own included.

The ordering of 1 and 2 is the second hard-won lesson here: check the rate
limit _before_ parsing/validating content, not after. If you validate first,
an invalid or oversized frame `continue`s past the rate-limit check on every
iteration — a flood of garbage frames never spends any budget, and the cap
you built exists and does nothing. Every inbound frame has to cost its
sender something, valid or not.

**3. One shared trust boundary.** `is_member(room, user_id)` is called by the
post-accept handshake check _and_ every REST route (`GET /rooms`,
`GET /rooms/{id}/messages`, `POST /rooms/{id}/read`). It is
never re-implemented per route. A permission rule that lives in one place
can only be wrong in one place; copy-pasted into three routes, it can drift
into three different, individually-plausible bugs. **This is the one file
you're expected to rewrite** (`membership.py`) — the example there (two
fixed participants) is the simplest possible stand-in for whatever "belongs
in this room" means in your app.

**4. Fan-out behind a swappable port.** `chat_broker.py`'s in-memory registry
is correct for a single process and silently wrong the moment you run more
than one — a sender on process A and a recipient on process B never see
each other's messages, no error, just a quietly broken product. Everything
that needs to deliver a message only ever calls `register` / `unregister` /
`publish` / `close_user`; swap the in-memory implementation for a Redis- or
NATS-backed one when you scale past one process, and nothing that calls it
changes. The same port is also what makes revocation _immediate_:
`close_user()` force-closes a live socket the instant your app decides
someone no longer belongs, rather than waiting for their next message.

**5. Identity always comes from the verified connection, never the payload.**
`sender_id` on every persisted and broadcast message is the value the
handshake verified — not anything read out of the incoming JSON. A client
claiming to be someone else in the message body is simply never looked at.

**6. The client never optimistically renders a sent message.** `chatStore.ts`
clears the input on submit but only shows the message once the server's own
broadcast arrives (the sender's own socket gets a copy — see #4). That keeps
one render path for every message, sender included, and the displayed
message always carries the server-assigned `id`/timestamp rather than a
locally-guessed one that might not match.

## Adapting this to your own app

- **`membership.py`** — always the first thing to change. Replace the body
  of `is_member()` with your app's real rule (a friends table, a
  project-members table, a paid-access flag, an invite that hasn't
  expired...). Keep the signature and keep it a live check, not a cached one.
- **`auth.py`** — delete it if you already have your own JWT issuing/verification.
  `chat_router.py` only needs a function shaped `str -> str | None` (token in,
  user id out, or `None`) — point it at your own.
- **`models.py`**'s `Room`\*\* — the reference uses two fixed participant ids
  because that's the simplest thing that demonstrates the pattern. A room
  with more than two members, or membership that comes from a join table
  instead of two columns, is a `membership.py` change, not a change to
  anything in `chat_router.py`.
- **The DB** — `db.py` is one SQLite file. Point `DATABASE_URL` at Postgres/
  MySQL/whatever; SQLModel's `Session` API doesn't change.
- **The broker** — stays in-memory until you run more than one server
  process. When you do, implement `ChatBroker`'s four methods against Redis
  pub/sub (or your infra's equivalent) and swap the module-level instance in
  `chat_broker.py` — nothing else changes.

## Two testing gotchas, if you write your own tests against this

Both are the same shape: a test double disagreeing with the real ASGI
server, in _opposite_ directions. Test against a real server (`uvicorn` +
a real `websockets` client) at least once before trusting either passed.

### Gotcha 1 — `TestClient` is _more permissive_ than a real server

Closing a WebSocket with a specific code (`websocket.close(code=4001, ...)`)
**before** calling `websocket.accept()` works fine against Starlette's
`TestClient` — it faithfully hands the close code to the test's client
object. Point a real client at a real `uvicorn` server doing the same thing
and you get a bare `HTTP 403 Forbidden` with the code silently gone: the
WebSocket protocol never got established, so there was never a close frame
for the code to ride on. This reference hit exactly this — see "The
architecture, in order" §1 above for the fix (`accept()` first, always).
**The lesson:** a check that runs before `accept()` needs testing against a
real server, not just `TestClient`, because `TestClient` will tell you it
works when it doesn't.

### Gotcha 2 — `TestClient` is _less permissive_ than a real server

If your test harness gives each simulated WebSocket connection its **own**
event loop — Starlette's `TestClient` does exactly this by default —
broadcasting between two connections open in the _same_ test will hang
forever. It's not a bug in the chat code: it's a cross-event-loop `await`
that async runtimes were never built to support, and it only exists because
the test harness (not your production server) gives each connection a
separate loop. Production never hits this — one process serves every
connection on one loop.

The fix, if you hit it: share one event loop/portal across a test client's
connections instead of letting each `websocket_connect()` spin up its own.
For Starlette's `TestClient` specifically, that means setting
`client.portal` to a portal you opened yourself, once, for the whole test —
see `anyio.from_thread.start_blocking_portal()` in `anyio`'s own docs, or
read `TestClient.__enter__`'s source for exactly what it does that
per-connection portals don't.
