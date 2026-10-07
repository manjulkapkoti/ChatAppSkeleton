// The hub: every room the caller belongs to, with an unread badge. In a
// real app this is usually reached from a persistent nav link (with the
// badge showing the total across all rooms) rather than any one specific
// page — chat is cross-cutting, not owned by one screen.
import { useEffect, useState } from 'react'
import { ChatStore } from './chatStore'
import { useChatStore } from './useChatStore'

interface Props {
  store: ChatStore
  onOpenRoom: (roomId: number) => void
}

export function RoomList({ store, onOpenRoom }: Props) {
  useChatStore(store)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    store
      .loadRooms()
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [store])

  if (loading) return <p>Loading…</p>
  if (error) return <p role="alert">Couldn't load your rooms.</p>
  if (store.rooms.length === 0) return <p>No conversations yet.</p>

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {store.rooms.map((room) => (
        <button
          key={room.id}
          onClick={() => onOpenRoom(room.id)}
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '10px 14px',
            border: '1px solid #e5e7eb',
            borderRadius: 8,
            background: '#fff',
            cursor: 'pointer',
          }}
        >
          <span>{room.counterpart_id}</span>
          {room.unread_count > 0 && (
            <span
              aria-label={`${room.unread_count} unread`}
              style={{
                minWidth: 20,
                height: 20,
                padding: '0 6px',
                borderRadius: 999,
                background: '#2563eb',
                color: '#fff',
                fontSize: 12,
                fontWeight: 700,
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {room.unread_count}
            </span>
          )}
        </button>
      ))}
    </div>
  )
}
