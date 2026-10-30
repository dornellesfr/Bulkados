import { createFileRoute } from '@tanstack/react-router'

import { MembersPage } from '@/components/groups/members-page'
import { membersQueryOptions } from '@/lib/api/groups'

export const Route = createFileRoute('/_app/grupos/$groupId/membros')({
  loader: ({ context, params }) =>
    Promise.all([
      context.queryClient.ensureQueryData(membersQueryOptions(params.groupId)),
    ]),
  component: MembersRoute,
})

function MembersRoute() {
  const { groupId } = Route.useParams()
  return <MembersPage groupId={groupId} />
}
