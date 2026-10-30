import { queryOptions } from '@tanstack/react-query'
import { z } from 'zod'

import { apiRequest } from '@/lib/api/client'

const catalogNameSchema = z.object({
  name_en: z.string(),
  name_pt: z.string().nullable(),
})

const targetDeckSchema = z.object({
  id: z.string(),
  name: z.string(),
})

const personSchema = z.object({
  id: z.string(),
  nick: z.string(),
})

export const handoffSchema = z.object({
  to_bring: z.array(
    z.object({
      id: z.string(),
      source: z.enum(['bulk', 'deck']),
      catalog: catalogNameSchema,
      requester: personSchema,
      target_deck: targetDeckSchema,
    }),
  ),
  to_receive: z.array(
    z.object({
      id: z.string(),
      source: z.enum(['bulk', 'deck']),
      catalog: catalogNameSchema,
      status: z.enum(['pending_acceptance', 'awaiting_handoff']),
      holder: personSchema,
      target_deck: targetDeckSchema,
    }),
  ),
})

export type Handoffs = z.infer<typeof handoffSchema>
export type HandoffBring = Handoffs['to_bring'][number]
export type HandoffReceive = Handoffs['to_receive'][number]

export const handoffKeys = {
  all: ['handoffs'] as const,
  list: (groupId: string) => ['handoffs', groupId] as const,
}

export async function listHandoffs(groupId: string, signal?: AbortSignal) {
  return apiRequest(`/groups/${groupId}/handoffs`, handoffSchema, { signal })
}

export async function requestCopy(deckId: string, cardCopyId: string) {
  return apiRequest(`/decks/${deckId}/requests`, z.unknown(), {
    method: 'POST',
    conflict: 'request',
    body: JSON.stringify({ card_copy_id: cardCopyId }),
  })
}

export async function acceptRequest(requestId: string) {
  return apiRequest(`/requests/${requestId}/accept`, z.unknown(), {
    method: 'POST',
    conflict: 'request',
  })
}

export async function rejectRequest(requestId: string) {
  return apiRequest(`/requests/${requestId}/reject`, z.unknown(), {
    method: 'POST',
    conflict: 'request',
  })
}

export async function cancelRequest(requestId: string) {
  return apiRequest(`/requests/${requestId}/cancel`, z.unknown(), {
    method: 'POST',
    conflict: 'request',
  })
}

export async function confirmRequest(requestId: string) {
  return apiRequest(`/requests/${requestId}/confirm`, z.unknown(), {
    method: 'POST',
    conflict: 'request',
  })
}

export function handoffsQueryOptions(groupId: string) {
  return queryOptions({
    queryKey: handoffKeys.list(groupId),
    queryFn: ({ signal }) => listHandoffs(groupId, signal),
  })
}
