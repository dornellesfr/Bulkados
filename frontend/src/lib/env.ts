import { z } from 'zod'

const envSchema = z.object({
  VITE_API_URL: z.url(),
})

const configuredUrl = import.meta.env.VITE_API_URL

if (typeof configuredUrl !== 'string' || configuredUrl.trim() === '') {
  throw new Error(
    'Defina VITE_API_URL com a origem da API, sem path. Exemplo: http://127.0.0.1:8000',
  )
}

export const env = envSchema.parse({
  VITE_API_URL: configuredUrl.replace(/\/+$/, ''),
})
