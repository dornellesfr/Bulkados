import { queryOptions } from '@tanstack/react-query'
import { z } from 'zod'

import { apiRequest } from '@/lib/api/client'

export const catalogCardSchema = z.object({
  oracle_id: z.string(),
  name_en: z.string(),
  name_pt: z.string().nullable(),
  mana_cost: z.string().nullable(),
  type_line: z.string().nullable(),
  color_identity: z.array(z.string()),
  is_basic: z.boolean(),
})

export type CatalogCard = z.infer<typeof catalogCardSchema>

export const catalogKeys = {
  search: (q: string) => ['catalog', q] as const,
}

export async function searchCatalog(q: string, signal?: AbortSignal) {
  const params = new URLSearchParams({ q })
  return apiRequest(
    `/catalog/cards?${params.toString()}`,
    z.array(catalogCardSchema),
    {
      signal,
    },
  )
}

export function catalogQueryOptions(q: string) {
  return queryOptions({
    queryKey: catalogKeys.search(q),
    queryFn: ({ signal }) => searchCatalog(q, signal),
  })
}
