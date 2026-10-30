import { createFileRoute } from '@tanstack/react-router'

import { HomePage } from '@/components/groups/home-page'
import { meQueryOptions } from '@/lib/api/auth'
import { groupsQueryOptions, invitationsQueryOptions } from '@/lib/api/groups'

export const Route = createFileRoute('/_app/')({
  loader: ({ context }) =>
    Promise.all([
      context.queryClient.ensureQueryData(meQueryOptions()),
      context.queryClient.ensureQueryData(groupsQueryOptions()),
      context.queryClient.ensureQueryData(invitationsQueryOptions()),
    ]),
  component: HomePage,
})
