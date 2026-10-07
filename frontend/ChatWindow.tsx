// Plain React + plain DOM elements — no UI library — so this is a starting
// point to restyle, not a component you're stuck with. The two things here
// that are security, not styling:
//
//  1. Messages render as `{message.text}` — text content, never
//     `dangerouslySetInnerHTML`. React escapes text content by default;
//     keep it that way. A chat message is the single most common place an
//     app accidentally builds an XSS hole for itself.
//  2. "Mine" vs "theirs" is decided by comparing `message.sender_id` to the
//     caller's OWN id — never trusted from anything the message claims
//     about itself, because nothing in the payload is trustworthy except
//     what the server chose to put there (and the server never echoes back
//     a client-supplied "this is you" flag — see chat_router.py).
import { useEffect, useState } from 'react'
import { ChatStore } from './chatStore'
import { useChatStore } from './useChatStore'

interface Props {
  store: ChatStore
  roomId: number
  currentUserId: string
}

export function ChatWindow({ store, roomId, currentUserId }: Props) {
  useChatStore(store) // subscribes this component to the store's updates
  const [text, setText] = useState('')
  const [historyLoaded, setHistoryLoaded] = useState(false)

  useEffect(() => {
    store.reset()
    store
      .loadHistory(roomId)
      .catch(() => {})
      .finally(() => setHistoryLoaded(true))
    void store.markRead(roomId)
    store.connect(roomId)
    return () => store.disconnect()
  }, [store, roomId])

  // "Updated while the window is open": every new message that arrives
  // while this component is mounted marks the room read again, not only on
  // the initial mount.
  useEffect(() => {
    if (store.messages.length > 0) void store.markRead(roomId)
  }, [store, store.messages.length, roomId])

  function submit(e: React.FormEvent) {
    e.preventDefault()
    const trimmed = text.trim()
    if (!trimmed) return
    store.send(trimmed)
    setText('')
  }

  if (!historyLoaded) return <p>Loading…</p>

  return (
    <div>
      {store.closeReason && <div role="alert">{store.closeReason}</div>}

      {store.messages.length === 0 ? (
        <p>No messages yet — say hello.</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 12 }}>
          {store.messages.map((message) => {
            const mine = message.sender_id === currentUserId
            return (
              <div
                key={message.id}
                data-testid={mine ? 'message-mine' : 'message-theirs'}
                style={{
                  alignSelf: mine ? 'flex-end' : 'flex-start',
                  background: mine ? '#2563eb' : '#e5e7eb',
                  color: mine ? '#fff' : '#111827',
                  padding: '8px 12px',
                  borderRadius: 12,
                  maxWidth: '75%',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                }}
              >
                {message.text}
              </div>
            )
          })}
        </div>
      )}

      <form onSubmit={submit} style={{ display: 'flex', gap: 8 }}>
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Type a message"
          style={{ flex: 1 }}
        />
        <button type="submit">Send</button>
      </form>
    </div>
  )
}
