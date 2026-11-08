import { queryOptions } from '@tanstack/react-query'
import { z } from 'zod'

import { ApiError, apiRequest } from '@/lib/api/client'
import {
  emailSchema,
  familyNameSchema,
  newPasswordSchema,
  passwordSchema,
  personNameSchema,
  tokenSchema,
} from '@/lib/api/schemas'
import { setSession } from '@/lib/auth/session'

export const loginInputSchema = z.object({
  email: emailSchema,
  password: passwordSchema,
})

export const registerInputSchema = z.object({
  first_name: personNameSchema,
  last_name: familyNameSchema,
  email: emailSchema,
  password: newPasswordSchema,
})

export const profileInputSchema = z.object({
  first_name: personNameSchema,
  last_name: familyNameSchema,
})

export const forgotPasswordInputSchema = z.object({
  email: emailSchema,
})

export const changePasswordInputSchema = z
  .object({
    current_password: z.string().min(1, 'Informe a senha atual.'),
    new_password: newPasswordSchema,
    confirm_password: z.string().min(1, 'Confirme a nova senha.'),
  })
  .refine((value) => value.new_password === value.confirm_password, {
    message: 'A confirmação não é igual à nova senha.',
    path: ['confirm_password'],
  })
  .refine((value) => value.new_password !== value.current_password, {
    message: 'A nova senha precisa ser diferente da atual.',
    path: ['new_password'],
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
  email: z.string(),
  first_name: z.string(),
  last_name: z.string(),
  created_at: z.string(),
})

export const entrarSearchSchema = z.object({
  redirect: z.string().optional(),
  aviso: z.literal('conta-criada').optional(),
})

export const forgotPasswordFallback =
  'Se existir uma conta com esse e-mail, enviamos as instruções para trocar a senha.'

export type LoginInput = z.infer<typeof loginInputSchema>
export type RegisterInput = z.infer<typeof registerInputSchema>
export type ProfileInput = z.infer<typeof profileInputSchema>
export type ForgotPasswordInput = z.infer<typeof forgotPasswordInputSchema>
export type ChangePasswordInput = z.infer<typeof changePasswordInputSchema>
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
      'O servidor respondeu de um jeito inesperado. Atualize a página.',
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

export async function changePassword(input: ChangePasswordInput) {
  const payload = changePasswordInputSchema.parse(input)
  await apiRequest('/auth/password', z.null(), {
    method: 'POST',
    body: JSON.stringify({
      current_password: payload.current_password,
      new_password: payload.new_password,
    }),
  })
}

export async function updateProfile(input: ProfileInput) {
  const payload = profileInputSchema.parse(input)
  return apiRequest('/me', meSchema, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
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
