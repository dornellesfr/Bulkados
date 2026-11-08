import {
  Link,
  createFileRoute,
  isNotFound,
  notFound,
} from '@tanstack/react-router'

import { GroupFrame } from '@/components/groups/group-frame'
import { Button } from '@/components/ui/button'
import { ApiError } from '@/lib/api/client'
import { groupsQueryOptions } from '@/lib/api/groups'
import { handoffsQueryOptions } from '@/lib/api/requests'

export const Route = createFileRoute('/_app/grupos/$groupId')({
  loader: async ({ context, params }) => {
    try {
      const groups =
        await context.queryClient.ensureQueryData(groupsQueryOptions())
      const group = groups.find((item) => item.id === params.groupId)

      if (!group) {
        throw notFound()
      }

      await context.queryClient.ensureQueryData(
        handoffsQueryOptions(params.groupId),
      )
    } catch (error) {
      if (isNotFound(error)) {
        throw error
      }

      if (error instanceof ApiError && error.status === 404) {
        throw notFound()
      }

      throw error
    }
  },
  component: GroupRoute,
  notFoundComponent: GroupUnavailable,
})

function GroupRoute() {
  const { groupId } = Route.useParams()
  return <GroupFrame groupId={groupId} />
}

function GroupUnavailable() {
  return (
    <div className="flex max-w-lg flex-col gap-4">
      <h1 className="font-heading text-lg font-medium">
        Esse grupo não está disponível.
      </h1>
      <Button type="button" variant="outline" className="w-fit" asChild>
        <Link to="/">Ir para o início</Link>
      </Button>
    </div>
  )
}
