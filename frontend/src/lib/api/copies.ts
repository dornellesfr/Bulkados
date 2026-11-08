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
  group_ids: z.array(z.string()),
})

export const bulkViewSchema = z.enum(['cartas', 'lista'])

export const bulkEstadoSchema = z.enum(['todas', 'available', 'in_deck'])

export const colorCodeSchema = z.enum(['W', 'U', 'B', 'R', 'G', 'C'])

export const manaBucketSchema = z.enum([
  '0',
  '1',
  '2',
  '3',
  '4',
  '5',
  '6',
  '7+',
])

const colorCodes = new Set<string>(colorCodeSchema.options)

export const bulkSearchSchema = z.object({
  q: z.string().trim().optional(),
  estado: bulkEstadoSchema.optional(),
  cores: z.union([z.string(), z.array(z.string())]).optional(),
  cmc: manaBucketSchema.optional(),
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
export type BulkEstado = z.infer<typeof bulkEstadoSchema>
export type BulkView = z.infer<typeof bulkViewSchema>
export type ColorCode = z.infer<typeof colorCodeSchema>
export type ManaBucket = z.infer<typeof manaBucketSchema>
export type CreateCopiesInput = z.infer<typeof createCopiesInputSchema>
export type BulkSearch = {
  q?: string
  estado?: BulkEstado
  cores?: Array<ColorCode>
  cmc?: ManaBucket
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

  const rawCores = parsed.cores ?? []
  const cores = (typeof rawCores === 'string' ? rawCores.split(',') : rawCores)
    .map((color) => color.trim().toUpperCase())
    .filter((color): color is ColorCode => colorCodes.has(color))

  if (cores.length > 0) {
    next.cores = [...new Set(cores)]
  }

  if (parsed.cmc) {
    next.cmc = parsed.cmc
  }

  if (parsed.destino) {
    next.destino = parsed.destino
  }

  return next
}

export function manaValue(cost: string | null): number {
  if (!cost) {
    return 0
  }

  const face = cost.split('//')[0] ?? cost
  const symbols = face.match(/\{[^}]+\}/g) ?? []

  return symbols.reduce((total, symbol) => {
    const inner = symbol.slice(1, -1).toUpperCase()

    if (inner === 'X') {
      return total
    }

    const numeric = Number.parseInt(inner, 10)

    if (!Number.isNaN(numeric)) {
      return total + numeric
    }

    return total + 1
  }, 0)
}

export function manaBucket(cost: string | null): ManaBucket {
  const value = manaValue(cost)

  return value >= 7 ? '7+' : (String(value) as ManaBucket)
}

export function filterCopies(copies: Array<Copy>, search: BulkSearch) {
  const needle = search.q?.toLocaleLowerCase('pt-BR')
  const estado = search.estado ?? 'available'
  const colors = search.cores ?? []

  return copies.filter((copy) => {
    if (estado === 'available' && copy.visibility !== 'available') {
      return false
    }

    if (estado === 'in_deck' && copy.visibility !== 'in_deck') {
      return false
    }

    if (colors.length > 0) {
      const identity =
        copy.catalog.color_identity.length === 0
          ? ['C']
          : copy.catalog.color_identity

      if (!colors.every((color) => identity.includes(color))) {
        return false
      }
    }

    if (search.cmc && manaBucket(copy.catalog.mana_cost) !== search.cmc) {
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
  return apiRequest(`/copies/${copyId}/groups`, copySchema, {
    method: 'POST',
    body: JSON.stringify({ group_id: groupId }),
  })
}

export async function unlinkCopy(copyId: string, groupId: string) {
  return apiRequest(`/copies/${copyId}/groups/${groupId}`, copySchema, {
    method: 'DELETE',
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
