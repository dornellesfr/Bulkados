import { useSyncExternalStore } from 'react'

const ACCESS_TOKEN_KEY = 'magic-bulk.access-token'
const REFRESH_TOKEN_KEY = 'magic-bulk.refresh-token'

export type SessionSnapshot =
  { status: 'in' } | { status: 'out'; reason: 'boot' | 'logout' | 'expired' }

const signedIn: SessionSnapshot = { status: 'in' }
const signedOutAtBoot: SessionSnapshot = { status: 'out', reason: 'boot' }

const listeners = new Set<() => void>()

function readStoredSession() {
  if (typeof localStorage === 'undefined') {
    return false
  }

  return Boolean(
    localStorage.getItem(ACCESS_TOKEN_KEY) &&
    localStorage.getItem(REFRESH_TOKEN_KEY),
  )
}

let snapshot: SessionSnapshot = readStoredSession() ? signedIn : signedOutAtBoot

function publish(next: SessionSnapshot) {
  if (snapshot.status === 'in' && next.status === 'in') {
    return
  }

  snapshot = next

  for (const listener of listeners) {
    listener()
  }
}

export function getSessionSnapshot() {
  return snapshot
}

export function subscribeSession(listener: () => void) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function hasSession() {
  return readStoredSession()
}

export function getAccessToken() {
  if (typeof localStorage === 'undefined') {
    return null
  }

  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function getRefreshToken() {
  if (typeof localStorage === 'undefined') {
    return null
  }

  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

export function setSession(accessToken: string, refreshToken: string) {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
  publish(signedIn)
}

export function clearSession(reason: 'logout' | 'expired') {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
  publish({ status: 'out', reason })
}

export function useSession() {
  return useSyncExternalStore(
    subscribeSession,
    getSessionSnapshot,
    () => signedOutAtBoot,
  )
}

if (typeof window !== 'undefined') {
  window.addEventListener('storage', () => {
    publish(
      readStoredSession() ? signedIn : { status: 'out', reason: 'expired' },
    )
  })
}
