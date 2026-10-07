// The React adapter for chatStore.ts — uses React's own `useSyncExternalStore`,
// no extra state library needed. A Vue app would instead wrap `subscribe` in
// a `ref` + `onMounted`/`onUnmounted`; a Svelte app would implement the
// store `subscribe` contract directly (chatStore.ts's shape already matches
// it closely). This file is the only React-specific piece in this reference.
import { useSyncExternalStore } from 'react'
import { ChatStore } from './chatStore'

export function useChatStore(store: ChatStore) {
  return useSyncExternalStore(
    (listener) => store.subscribe(listener),
    () => store, // the store mutates itself; returning the same reference is fine here
  )
}
