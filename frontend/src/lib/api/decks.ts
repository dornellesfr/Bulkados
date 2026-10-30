import { queryOptions } from '@tanstack/react-query'
import { z } from 'zod'

import { apiRequest } from '@/lib/api/client'
import {
  deckCatalogSchema,
  deckFormatSchema,
  deckNameSchema,
  openRequestSchema,
  personSchema,
  quantitySchema,
} from '@/lib/api/schemas'

export const deckWarningSchema = z.object({
  code: z.string(),
  card_copy_id: z.string().nullable(),
  message: z.string(),
})

export const deckCardSchema = z.object({
  card_copy_id: z.string(),
  role: z.enum(['commander', 'main']),
  locked: z.boolean(),
  price_cents: z.number().int().nullable(),
  holder: personSchema,
  catalog: deckCatalogSchema,
  open_request: openRequestSchema.nullable(),
  can_toggle_commander: z.boolean(),
})

export const deckCommanderSchema = z.object({
  name_en: z.string(),
  name_pt: z.string().nullable(),
  image_url: z.string().nullable(),
})

export const deckSummarySchema = z.object({
  id: z.string(),
  name: z.string(),
  format: deckFormatSchema,
  color_identity: z.array(z.string()).nullable(),
  color_identity_name: z.string().nullable(),
  commanders: z.array(deckCommanderSchema),
})

export const deckDetailSchema = z.object({
  id: z.string(),
  group_id: z.string(),
  name: z.string(),
  format: deckFormatSchema,
  owner_id: z.string(),
  color_identity: z.array(z.string()).nullable(),
  color_identity_name: z.string().nullable(),
  card_count: z.number().int(),
  main_price_cents: z.number().int(),
  commander_price_cents: z.number().int(),
  warnings: z.array(deckWarningSchema),
  cards: z.array(deckCardSchema),
})

export const createDeckInputSchema = z.object({
  name: deckNameSchema,
  format: deckFormatSchema,
})

export const updateDeckInputSchema = z.object({
  name: deckNameSchema.optional(),
  format: deckFormatSchema.optional(),
})

export const deckCopiesInputSchema = z.object({
  oracle_id: z.string().min(1),
  quantity: quantitySchema,
})

export type DeckWarning = z.infer<typeof deckWarningSchema>
export type DeckCard = z.infer<typeof deckCardSchema>
export type DeckSummary = z.infer<typeof deckSummarySchema>
export type DeckDetail = z.infer<typeof deckDetailSchema>
export type CreateDeckInput = z.infer<typeof createDeckInputSchema>
export type UpdateDeckInput = z.infer<typeof updateDeckInputSchema>

export const deckKeys = {
  all: ['decks'] as const,
  list: (groupId: string) => ['decks', 'list', groupId] as const,
  detail: (deckId: string) => ['decks', 'detail', deckId] as const,
}

export async function listDecks(groupId: string, signal?: AbortSignal) {
  return apiRequest(`/groups/${groupId}/decks`, z.array(deckSummarySchema), {
    signal,
  })
}

export async function createDeck(groupId: string, input: CreateDeckInput) {
  const payload = createDeckInputSchema.parse(input)
  return apiRequest(`/groups/${groupId}/decks`, deckSummarySchema, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function getDeck(deckId: string, signal?: AbortSignal) {
  return apiRequest(`/decks/${deckId}`, deckDetailSchema, { signal })
}

export async function updateDeck(deckId: string, input: UpdateDeckInput) {
  const payload = updateDeckInputSchema.parse(input)
  return apiRequest(`/decks/${deckId}`, deckDetailSchema, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export async function deleteDeck(deckId: string) {
  return apiRequest(`/decks/${deckId}`, z.unknown(), {
    method: 'DELETE',
  })
}

export async function setCommanders(
  deckId: string,
  cardCopyIds: Array<string>,
) {
  return apiRequest(`/decks/${deckId}/commanders`, z.unknown(), {
    method: 'POST',
    body: JSON.stringify({ card_copy_ids: cardCopyIds }),
  })
}

export async function takeCopy(deckId: string, cardCopyId: string) {
  return apiRequest(`/decks/${deckId}/take`, z.unknown(), {
    method: 'POST',
    conflict: 'request',
    body: JSON.stringify({ card_copy_id: cardCopyId }),
  })
}

export async function addDeckCopies(
  deckId: string,
  input: z.infer<typeof deckCopiesInputSchema>,
) {
  const payload = deckCopiesInputSchema.parse(input)
  return apiRequest(`/decks/${deckId}/copies`, z.unknown(), {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function moveDeckCard(
  deckId: string,
  cardCopyId: string,
  targetDeckId: string,
) {
  return apiRequest(`/decks/${deckId}/cards/${cardCopyId}/move`, z.unknown(), {
    method: 'POST',
    body: JSON.stringify({ target_deck_id: targetDeckId }),
  })
}

export async function returnDeckCard(deckId: string, cardCopyId: string) {
  return apiRequest(
    `/decks/${deckId}/cards/${cardCopyId}/return`,
    z.unknown(),
    { method: 'POST' },
  )
}

export async function lockDeckCard(deckId: string, cardCopyId: string) {
  return apiRequest(`/decks/${deckId}/cards/${cardCopyId}/lock`, z.unknown(), {
    method: 'POST',
  })
}

export async function unlockDeckCard(deckId: string, cardCopyId: string) {
  return apiRequest(
    `/decks/${deckId}/cards/${cardCopyId}/unlock`,
    z.unknown(),
    { method: 'POST' },
  )
}

export function decksQueryOptions(groupId: string) {
  return queryOptions({
    queryKey: deckKeys.list(groupId),
    queryFn: ({ signal }) => listDecks(groupId, signal),
  })
}

export function deckQueryOptions(deckId: string) {
  return queryOptions({
    queryKey: deckKeys.detail(deckId),
    queryFn: ({ signal }) => getDeck(deckId, signal),
  })
}
