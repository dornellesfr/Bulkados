import { z } from 'zod'

export const tokenSchema = z.object({
  access_token: z.string(),
  refresh_token: z.string(),
  expires_in: z.number(),
})

export const personSchema = z.object({
  id: z.string(),
  email: z.string(),
  first_name: z.string(),
  last_name: z.string(),
})

export function personName(person: { first_name: string; last_name: string }) {
  return `${person.first_name} ${person.last_name}`
}

export const deckFormatSchema = z.enum([
  'commander_10',
  'commander_100',
  'commander_200',
  'commander_500',
  'competitive',
])

export const partnerKindSchema = z.enum([
  'partner',
  'partner_with',
  'friends_forever',
  'background',
  'choose_a_background',
  'doctors_companion',
])

export const openRequestSchema = z.object({
  id: z.string(),
  status: z.enum(['pending_acceptance', 'awaiting_handoff']),
  source: z.enum(['bulk', 'deck']),
  requester: personSchema,
})

export const copyCatalogSchema = z.object({
  oracle_id: z.string(),
  name_en: z.string(),
  name_pt: z.string().nullable(),
  image_url: z.string().nullable(),
  mana_cost: z.string().nullable(),
  type_line: z.string().nullable(),
  oracle_text: z.string(),
  color_identity: z.array(z.string()),
  is_basic: z.boolean(),
  keywords: z.array(z.string()),
  can_be_commander: z.boolean(),
  partner_kind: partnerKindSchema.nullable(),
})

export const deckCatalogSchema = copyCatalogSchema.extend({
  commander_legal: z.enum(['legal', 'banned', 'not_legal']),
})

export const emailSchema = z.email('Informe um e-mail válido.')

export const personNameSchema = z
  .string()
  .trim()
  .min(1, 'Informe o nome.')
  .max(80, 'Use no máximo 80 caracteres.')

export const familyNameSchema = z
  .string()
  .trim()
  .min(1, 'Informe o sobrenome.')
  .max(80, 'Use no máximo 80 caracteres.')

export const groupNameSchema = z
  .string()
  .trim()
  .min(1, 'Informe o nome.')
  .max(80, 'Use no máximo 80 caracteres.')

export const deckNameSchema = z.string().trim().min(1, 'Informe o nome.')

export const quantitySchema = z
  .number('Informe a quantidade.')
  .int('Use um número inteiro.')
  .min(1, 'A quantidade mínima é 1.')
  .max(99, 'A quantidade máxima é 99.')

export const passwordSchema = z.string().min(1, 'Informe a senha.')

export const newPasswordSchema = z
  .string()
  .min(6, 'Use pelo menos 6 caracteres.')
  .max(128, 'Use no máximo 128 caracteres.')

export type Person = z.infer<typeof personSchema>
export type DeckFormat = z.infer<typeof deckFormatSchema>
export type OpenRequest = z.infer<typeof openRequestSchema>
export type PartnerKind = z.infer<typeof partnerKindSchema>
