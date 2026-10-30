import { queryOptions } from '@tanstack/react-query'
import { z } from 'zod'

import { apiRequest } from '@/lib/api/client'
import {
  copyCatalogSchema,
  openRequestSchema,
  personSchema,
  quantitySchema,
} from '@/lib/api/schemas'

export const copyVisibilitySchema = z.enum([
  'available',
  'reserved',
  'in_deck',
  'in_use_elsewhere',
])

export const copySchema = z.object({
  id: z.string(),
  catalog: copyCatalogSchema,
  holder: personSchema,
  added_by: personSchema,
  price_cents: z.number().int().nullable(),
  price_fetched_at: z.string().nullable(),
  state: z.enum(['available', 'reserved', 'in_deck']),
  locked: z.boolean(),
  visibility: copyVisibilitySchema,
  deck: z
    .object({
      id: z.string(),
      name: z.string(),
      owner: personSchema,
    })
    .nullable(),
  open_request: openRequestSchema.nullable(),
})

export const bulkSearchSchema = z.object({
  q: z.string().trim().optional(),
  estado: copyVisibilitySchema.optional(),
  destino: z.string().optional(),
})

export const createCopiesInputSchema = z.object({
  oracle_id: z.string().min(1),
  quantity: quantitySchema,
  holder_id: z.string().min(1).optional(),
  group_ids: z.array(z.string().min(1)).optional(),
})

export type Copy = z.infer<typeof copySchema>
export type CopyVisibility = z.infer<typeof copyVisibilitySchema>
export type CreateCopiesInput = z.infer<typeof createCopiesInputSchema>
export type BulkSearch = {
  q?: string
  estado?: CopyVisibility
  destino?: string
}

export function parseBulkSearch(search: Record<string, unknown>): BulkSearch {
  const parsed = bulkSearchSchema.parse(search)
  const next: BulkSearch = {}

  if (parsed.q) {
    next.q = parsed.q
  }

  if (parsed.estado) {
    next.estado = parsed.estado
  }

  if (parsed.destino) {
    next.destino = parsed.destino
  }

  return next
}

export function filterCopies(copies: Array<Copy>, search: BulkSearch) {
  const needle = search.q?.toLocaleLowerCase('pt-BR')

  return copies.filter((copy) => {
    if (search.estado && copy.visibility !== search.estado) {
      return false
    }

    if (!needle) {
      return true
    }

    const names = `${copy.catalog.name_pt ?? ''} ${copy.catalog.name_en}`
    return names.toLocaleLowerCase('pt-BR').includes(needle)
  })
}

export const copyKeys = {
  all: ['copies'] as const,
  list: (groupId: string) => ['copies', groupId] as const,
}

export async function listCopies(groupId: string, signal?: AbortSignal) {
  return apiRequest(`/groups/${groupId}/copies`, z.array(copySchema), {
    signal,
  })
}

export async function createCopies(groupId: string, input: CreateCopiesInput) {
  const payload = createCopiesInputSchema.parse(input)
  return apiRequest(`/groups/${groupId}/copies`, z.array(copySchema), {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function shareCopy(copyId: string, groupId: string) {
  return apiRequest(`/copies/${copyId}/groups`, z.unknown(), {
    method: 'POST',
    body: JSON.stringify({ group_id: groupId }),
  })
}

export async function deleteCopy(copyId: string) {
  return apiRequest(`/copies/${copyId}`, z.unknown(), {
    method: 'DELETE',
  })
}

export async function refreshCopyPrice(copyId: string) {
  return apiRequest(`/copies/${copyId}/refresh-price`, copySchema, {
    method: 'POST',
  })
}

export function copiesQueryOptions(groupId: string) {
  return queryOptions({
    queryKey: copyKeys.list(groupId),
    queryFn: ({ signal }) => listCopies(groupId, signal),
  })
}
