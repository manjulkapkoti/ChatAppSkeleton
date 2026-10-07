// Framework-agnostic on purpose: no MobX, no Redux, no React import. It's a
// plain class with a tiny built-in subscribe/notify, so it plugs into React
// (via `useSyncExternalStore` — see `useChatStore.ts`, no extra library
// needed), Vue, Svelte, or vanilla JS equally. Copy this file and its
// sibling `useChatStore.ts` into any project; nothing else in `frontend/`
// is required for the store itself to work.

export interface RoomSummary {
  id: number
  counterpart_id: string
  unread_count: number
}

export interface ChatMessage {
  id: number
  room_id: number
  sender_id: string
  text: string
  created_at: string
}

export type ChatConnectionStatus = 'idle' | 'loading' | 'connected' | 'closed' | 'error'

// One message per close code, everything else shows nothing — see the
// architecture diagram / README for why these four codes exist. Note: 4001,
// 4003, and 4009 are all sent by chat_router.py today; 4004 is wired up here
// for when YOUR app calls chat_broker.close_user(..., code=4004) to force-
// close someone mid-conversation — this reference doesn't demo that call itself.
const CLOSE_CODE_MESSAGES: Record<number, string> = {
  4001: 'Your session expired — please log in again.',
  4003: 'You no longer have access to this room.',
  4004: 'Your access to this room was revoked.',
  4009: "You're sending messages too fast — please slow down.",
}

// Swap these two functions for however your app talks to its own backend —
// they're the only place this file assumes an HTTP/WS layer's shape.
async function apiGet(path: string, token: string): Promise<unknown> {
  const res = await fetch(`/api${path}`, { headers: { Authorization: `Bearer ${token}` } })
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
  return res.status === 204 ? null : res.json()
}

async function apiPost(path: string, token: string): Promise<void> {
  const res = await fetch(`/api${path}`, { method: 'POST', headers: { Authorization: `Bearer ${token}` } })
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`)
}

export class ChatStore {
  rooms: RoomSummary[] = []
  messages: ChatMessage[] = []
  status: ChatConnectionStatus = 'idle'
  closeReason: string | null = null

  private socket: WebSocket | null = null
  private listeners = new Set<() => void>()
  private getToken: () => string

  constructor(getToken: () => string) {
    this.getToken = getToken
  }

  // ── the subscribe/notify pair every framework adapter needs ──────────────

  subscribe(listener: () => void): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  private notify(): void {
    for (const listener of this.listeners) listener()
  }

  // ── REST reads ────────────────────────────────────────────────────────────

  async loadRooms(): Promise<void> {
    this.rooms = (await apiGet('/rooms', this.getToken())) as RoomSummary[]
    this.notify()
  }

  async loadHistory(roomId: number): Promise<void> {
    const rows = (await apiGet(`/rooms/${roomId}/messages`, this.getToken())) as ChatMessage[]
    this.messages = [...rows].reverse() // server returns newest-first; the window renders oldest-first
    this.notify()
  }

  async markRead(roomId: number): Promise<void> {
    await apiPost(`/rooms/${roomId}/read`, this.getToken())
  }

  // ── the WebSocket lifecycle ────────────────────────────────────────────────

  /** Token travels as a query param — a browser can't attach a custom header
   * to a WebSocket handshake. See the architecture README for the security
   * note on what this means in production (wss://, token lifetime). */
  connect(roomId: number): void {
    this.status = 'loading'
    this.closeReason = null
    this.notify()

    const socket = new WebSocket(`/ws/rooms/${roomId}?token=${encodeURIComponent(this.getToken())}`)

    socket.onopen = () => {
      this.status = 'connected'
      this.notify()
    }

    socket.onmessage = (event) => {
      let frame: { type?: string; [key: string]: unknown }
      try {
        frame = JSON.parse(event.data as string)
      } catch {
        return
      }
      if (frame.type === 'message') {
        this.messages = [...this.messages, frame as unknown as ChatMessage]
        this.notify()
      }
      // error frames (invalid_message / message_too_long) are non-fatal by
      // design — nothing to do at the store level; the input simply wasn't sent.
    }

    socket.onclose = (event) => {
      this.status = 'closed'
      this.closeReason = CLOSE_CODE_MESSAGES[event.code] ?? null
      this.notify()
    }

    this.socket = socket
  }

  disconnect(): void {
    this.socket?.close()
    this.socket = null
  }

  /** Sends `{text}` only — never a client-guessed id, sender, or timestamp.
   * Identity comes from the connection the server already verified, never
   * from anything the client claims in the payload. */
  send(text: string): void {
    this.socket?.send(JSON.stringify({ text }))
  }

  reset(): void {
    this.disconnect()
    this.rooms = []
    this.messages = []
    this.status = 'idle'
    this.closeReason = null
    this.notify()
  }
}
