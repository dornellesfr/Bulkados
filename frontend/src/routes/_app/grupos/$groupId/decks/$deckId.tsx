import { createFileRoute } from '@tanstack/react-router'

import { DeckPage } from '@/components/decks/deck-page'
import { deckQueryOptions } from '@/lib/api/decks'

export const Route = createFileRoute('/_app/grupos/$groupId/decks/$deckId')({
  loader: ({ context, params }) =>
    context.queryClient.ensureQueryData(deckQueryOptions(params.deckId)),
  component: DeckRoute,
})

function DeckRoute() {
  const { groupId, deckId } = Route.useParams()
  return <DeckPage groupId={groupId} deckId={deckId} />
}
