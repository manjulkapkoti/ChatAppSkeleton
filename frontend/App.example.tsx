// Not a file to copy verbatim — it's here to show how the pieces wire
// together in a real app: one `ChatStore` instance (however your app
// prefers to hold it — a module singleton, a React context, a DI
// container), a token getter that reads from wherever your app already
// keeps its auth token, and simple state to switch between the room list
// and an open room.
import { useState } from 'react'
import { ChatStore } from './chatStore'
import { RoomList } from './RoomList'
import { ChatWindow } from './ChatWindow'

// Point this at however your app stores its own auth token.
const chatStore = new ChatStore(() => localStorage.getItem('token') ?? '')
const currentUserId = 'alice' // from your app's own auth/session state

export function ChatExampleApp() {
  const [openRoomId, setOpenRoomId] = useState<number | null>(null)

  if (openRoomId !== null) {
    return (
      <div>
        <button onClick={() => setOpenRoomId(null)}>&larr; back to rooms</button>
        <ChatWindow store={chatStore} roomId={openRoomId} currentUserId={currentUserId} />
      </div>
    )
  }

  return (
    <div>
      <h1>Messages</h1>
      <RoomList store={chatStore} onOpenRoom={setOpenRoomId} />
    </div>
  )
}
