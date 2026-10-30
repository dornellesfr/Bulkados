import { createFileRoute } from '@tanstack/react-router'

import { HandoffPage } from '@/components/requests/handoff-page'
import { handoffsQueryOptions } from '@/lib/api/requests'

export const Route = createFileRoute('/_app/grupos/$groupId/encontro')({
  loader: ({ context, params }) =>
    context.queryClient.ensureQueryData(handoffsQueryOptions(params.groupId)),
  component: HandoffRoute,
})

function HandoffRoute() {
  const { groupId } = Route.useParams()
  return <HandoffPage groupId={groupId} />
}
