import { createFileRoute } from '@tanstack/react-router'

import { BulkPage } from '@/components/copies/bulk-page'
import { copiesQueryOptions, parseBulkSearch } from '@/lib/api/copies'
import type { BulkSearch } from '@/lib/api/copies'
import { decksQueryOptions } from '@/lib/api/decks'

export const Route = createFileRoute('/_app/grupos/$groupId/')({
  validateSearch: parseBulkSearch,
  loader: ({ context, params }) =>
    Promise.all([
      context.queryClient.ensureQueryData(copiesQueryOptions(params.groupId)),
      context.queryClient.ensureQueryData(decksQueryOptions(params.groupId)),
    ]),
  component: BulkRoute,
})

function cleanSearch(search: BulkSearch): BulkSearch {
  return {
    ...(search.q ? { q: search.q } : {}),
    ...(search.estado ? { estado: search.estado } : {}),
    ...(search.destino ? { destino: search.destino } : {}),
  }
}

function BulkRoute() {
  const { groupId } = Route.useParams()
  const search = Route.useSearch()
  const navigate = Route.useNavigate()

  return (
    <BulkPage
      groupId={groupId}
      search={search}
      onSearchChange={(next) => {
        void navigate({ search: cleanSearch(next) })
      }}
    />
  )
}
