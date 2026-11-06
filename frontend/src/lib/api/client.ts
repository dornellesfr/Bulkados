import type { z } from 'zod'

import {
  clearSession,
  getAccessToken,
  getRefreshToken,
  sessionEpoch,
  setSession,
} from '@/lib/auth/session'
import { tokenSchema } from '@/lib/api/schemas'
import { env } from '@/lib/env'

export class ApiError extends Error {
  readonly status: number
  readonly issues?: unknown

  constructor(message: string, status: number, issues?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.issues = issues
  }
}

type ErrorKind = {
  conflict?: 'request' | 'invitation'
  notFoundMessage?: string
}

type ApiRequestInit = Omit<RequestInit, 'headers'> &
  ErrorKind & {
    headers?: HeadersInit
    auth?: boolean
    retried?: boolean
    refresh?: boolean
  }

let refreshInFlight: Promise<boolean> | null = null

export function apiErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    return error.message
  }

  return 'Não foi possível concluir. Tente de novo.'
}

function fallbackMessage(status: number, kind: ErrorKind) {
  if (status === 404) {
    return kind.notFoundMessage ?? 'Esse recurso não está disponível.'
  }

  if (status === 409 && kind.conflict === 'request') {
    return 'Essa carta acabou de ser reservada por outra pessoa.'
  }

  if (status === 409 && kind.conflict === 'invitation') {
    return 'Essa pessoa já foi convidada ou já está no grupo.'
  }

  if (status === 422) {
    return 'Revise os campos e tente de novo.'
  }

  return 'Não foi possível concluir. Tente de novo.'
}

function validationMessage(detail: unknown[]) {
  const fields = detail.flatMap((item) => {
    if (!item || typeof item !== 'object' || !('loc' in item)) {
      return []
    }

    const loc = item.loc

    if (!Array.isArray(loc) || loc.length === 0) {
      return []
    }

    const field = loc[loc.length - 1]
    return typeof field === 'string' ? [field] : []
  })

  if (fields.some((field) => field === 'email')) {
    return 'Informe um e-mail válido.'
  }

  if (fields.some((field) => field.includes('password'))) {
    return 'A senha precisa ter de 6 a 128 caracteres.'
  }

  return 'Revise os campos e tente de novo.'
}

function messageFromPayload(payload: unknown, status: number, kind: ErrorKind) {
  const detail =
    payload && typeof payload === 'object' && 'detail' in payload
      ? payload.detail
      : undefined

  if (typeof detail === 'string' && detail.trim()) {
    return detail.trim()
  }

  if (Array.isArray(detail)) {
    return validationMessage(detail)
  }

  return fallbackMessage(status, kind)
}

async function readPayload(response: Response) {
  if (response.status === 204) {
    return null
  }

  const text = await response.text()

  if (text.trim() === '') {
    return null
  }

  try {
    return JSON.parse(text) as unknown
  } catch {
    throw new ApiError(
      'O servidor respondeu de um jeito inesperado. Atualize a página.',
      response.status,
    )
  }
}

async function toApiError(response: Response, kind: ErrorKind) {
  let payload: unknown = null

  try {
    payload = await readPayload(response)
  } catch (error) {
    if (error instanceof ApiError) {
      return error
    }
  }

  return new ApiError(
    messageFromPayload(payload, response.status, kind),
    response.status,
  )
}

async function performRefresh() {
  const atEpoch = sessionEpoch()
  const refreshToken = getRefreshToken()

  if (!refreshToken) {
    return false
  }

  try {
    const tokens = await apiRequest('/auth/refresh', tokenSchema, {
      method: 'POST',
      auth: false,
      refresh: true,
      body: JSON.stringify({ refresh_token: refreshToken }),
    })

    if (sessionEpoch() !== atEpoch) {
      return false
    }

    setSession(tokens.access_token, tokens.refresh_token)
    return true
  } catch {
    return false
  }
}

function refreshOnce() {
  if (!refreshInFlight) {
    refreshInFlight = performRefresh().finally(() => {
      refreshInFlight = null
    })
  }

  return refreshInFlight
}

export async function apiRequest<TSchema extends z.ZodType>(
  path: string,
  schema: TSchema,
  init?: ApiRequestInit,
): Promise<z.infer<TSchema>> {
  const {
    auth = true,
    conflict,
    notFoundMessage,
    retried = false,
    refresh = false,
    headers: initHeaders,
    ...requestInit
  } = init ?? {}

  const headers = new Headers(initHeaders)
  headers.set('Accept', 'application/json')

  if (requestInit.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  if (auth) {
    const accessToken = getAccessToken()

    if (accessToken) {
      headers.set('Authorization', `Bearer ${accessToken}`)
    }
  }

  let response: Response

  try {
    response = await fetch(`${env.VITE_API_URL}/api/v1${path}`, {
      ...requestInit,
      headers,
    })
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw error
    }

    throw new ApiError('Sem conexão. Tente de novo.', 0)
  }

  if (response.status === 401 && auth && !refresh) {
    const atEpoch = sessionEpoch()

    if (!retried) {
      const refreshed = await refreshOnce()

      if (refreshed || sessionEpoch() !== atEpoch) {
        return apiRequest(path, schema, { ...init, retried: true })
      }
    }

    clearSession('expired', atEpoch)
    throw new ApiError('Sua sessão expirou. Entre de novo.', 401)
  }

  if (!response.ok) {
    throw await toApiError(response, { conflict, notFoundMessage })
  }

  const payload = await readPayload(response)
  const parsed = schema.safeParse(payload)

  if (!parsed.success) {
    throw new ApiError(
      'O servidor respondeu de um jeito inesperado. Atualize a página.',
      response.status,
      parsed.error.issues,
    )
  }

  return parsed.data
}
