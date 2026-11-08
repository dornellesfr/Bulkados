import { createFileRoute } from '@tanstack/react-router'

import { DecksPage } from '@/components/decks/decks-page'
import { decksQueryOptions } from '@/lib/api/decks'

export const Route = createFileRoute('/_app/grupos/$groupId/decks/')({
  loader: ({ context }) =>
    context.queryClient.ensureQueryData(decksQueryOptions()),
  component: DecksRoute,
})

function DecksRoute() {
  const { groupId } = Route.useParams()
  return <DecksPage groupId={groupId} />
}
