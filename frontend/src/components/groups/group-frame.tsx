import { useSuspenseQuery } from '@tanstack/react-query'
import { Link, Outlet, notFound } from '@tanstack/react-router'

import { Badge } from '@/components/ui/badge'
import { handoffsQueryOptions } from '@/lib/api/requests'
import { groupsQueryOptions } from '@/lib/api/groups'

export function GroupFrame({ groupId }: { groupId: string }) {
  const { data: groups } = useSuspenseQuery(groupsQueryOptions())
  const { data: handoffs } = useSuspenseQuery(handoffsQueryOptions(groupId))
  const group = groups.find((item) => item.id === groupId)
  const handoffCount = handoffs.to_bring.length + handoffs.to_receive.length

  if (!group) {
    throw notFound()
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-3">
        <p className="text-sm text-muted-foreground">{group.name}</p>
        <nav className="flex flex-wrap gap-2 text-sm">
          <Link
            to="/grupos/$groupId"
            params={{ groupId }}
            activeOptions={{ exact: true }}
            className="rounded-full px-3 py-1 text-muted-foreground"
            activeProps={{
              className: 'rounded-full bg-muted px-3 py-1 text-foreground',
            }}
          >
            Bulk
          </Link>
          <Link
            to="/grupos/$groupId/decks"
            params={{ groupId }}
            className="rounded-full px-3 py-1 text-muted-foreground"
            activeProps={{
              className: 'rounded-full bg-muted px-3 py-1 text-foreground',
            }}
          >
            Decks
          </Link>
          <Link
            to="/grupos/$groupId/encontro"
            params={{ groupId }}
            activeOptions={{ exact: true }}
            className="inline-flex items-center gap-2 rounded-full px-3 py-1 text-muted-foreground"
            activeProps={{
              className:
                'inline-flex items-center gap-2 rounded-full bg-muted px-3 py-1 text-foreground',
            }}
          >
            Encontro
            {handoffCount > 0 ? (
              <Badge variant="secondary">{handoffCount}</Badge>
            ) : null}
          </Link>
          <Link
            to="/grupos/$groupId/membros"
            params={{ groupId }}
            activeOptions={{ exact: true }}
            className="rounded-full px-3 py-1 text-muted-foreground"
            activeProps={{
              className: 'rounded-full bg-muted px-3 py-1 text-foreground',
            }}
          >
            Membros
          </Link>
        </nav>
      </div>
      <Outlet />
    </div>
  )
}
