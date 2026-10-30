import { queryOptions } from '@tanstack/react-query'
import { z } from 'zod'

import { ApiError, apiRequest } from '@/lib/api/client'
import {
  identifierSchema,
  nickSchema,
  passwordSchema,
  tokenSchema,
} from '@/lib/api/schemas'
import { setSession } from '@/lib/auth/session'

export const loginInputSchema = z.object({
  identifier: identifierSchema,
  password: passwordSchema,
})

export const registerInputSchema = z.object({
  email: z.email('Informe um e-mail válido.'),
  password: passwordSchema,
  nick: nickSchema,
})

export const forgotPasswordInputSchema = z.object({
  identifier: identifierSchema,
})

const registerResponseSchema = z.object({
  access_token: z.string().optional(),
  refresh_token: z.string().optional(),
  expires_in: z.number().optional(),
})

const forgotPasswordResponseSchema = z.object({
  message: z.string().optional(),
})

export const meSchema = z.object({
  id: z.string(),
  nick: z.string(),
})

export const entrarSearchSchema = z.object({
  redirect: z.string().optional(),
  aviso: z.literal('conta-criada').optional(),
})

export const forgotPasswordFallback =
  'Se existir uma conta, o e-mail de recuperação foi enviado.'

export type LoginInput = z.infer<typeof loginInputSchema>
export type RegisterInput = z.infer<typeof registerInputSchema>
export type ForgotPasswordInput = z.infer<typeof forgotPasswordInputSchema>
export type Me = z.infer<typeof meSchema>
export type EntrarSearch = {
  redirect?: string
  aviso?: 'conta-criada'
}

export function parseEntrarSearch(
  search: Record<string, unknown>,
): EntrarSearch {
  const parsed = entrarSearchSchema.parse(search)
  const next: EntrarSearch = {}

  if (parsed.redirect) {
    next.redirect = parsed.redirect
  }

  if (parsed.aviso) {
    next.aviso = parsed.aviso
  }

  return next
}

export const authKeys = {
  me: ['me'] as const,
}

export async function login(input: LoginInput) {
  const payload = loginInputSchema.parse(input)
  const tokens = await apiRequest('/auth/login', tokenSchema, {
    method: 'POST',
    auth: false,
    body: JSON.stringify(payload),
  })
  setSession(tokens.access_token, tokens.refresh_token)
  return tokens
}

export async function register(input: RegisterInput) {
  const payload = registerInputSchema.parse(input)
  const data = await apiRequest('/auth/register', registerResponseSchema, {
    method: 'POST',
    auth: false,
    body: JSON.stringify(payload),
  })

  const hasTokenField =
    data.access_token != null ||
    data.refresh_token != null ||
    data.expires_in != null

  if (data.access_token && data.refresh_token && data.expires_in != null) {
    setSession(data.access_token, data.refresh_token)
    return { session: true as const }
  }

  if (hasTokenField) {
    throw new ApiError(
      'A resposta da API não confere com o contrato esperado.',
      200,
    )
  }

  return { session: false as const }
}

export async function forgotPassword(input: ForgotPasswordInput) {
  const payload = forgotPasswordInputSchema.parse(input)
  const data = await apiRequest(
    '/auth/forgot-password',
    forgotPasswordResponseSchema,
    {
      method: 'POST',
      auth: false,
      body: JSON.stringify(payload),
    },
  )

  const message = data.message?.trim()
  return message ? message : forgotPasswordFallback
}

export async function getMe(signal?: AbortSignal) {
  return apiRequest('/me', meSchema, { signal })
}

export function meQueryOptions() {
  return queryOptions({
    queryKey: authKeys.me,
    queryFn: ({ signal }) => getMe(signal),
  })
}
