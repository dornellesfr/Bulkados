import { useState } from 'react'
import { useSuspenseQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'

import { PageHeader } from '@/components/layout/page-header'
import { CreateGroupDialog } from '@/components/groups/create-group-dialog'
import { InvitationList } from '@/components/groups/invitation-list'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { meQueryOptions } from '@/lib/api/auth'
import { groupsQueryOptions, invitationsQueryOptions } from '@/lib/api/groups'

export function HomePage() {
  const { data: groups } = useSuspenseQuery(groupsQueryOptions())
  const { data: invitations } = useSuspenseQuery(invitationsQueryOptions())
  const { data: me } = useSuspenseQuery(meQueryOptions())
  const [createOpen, setCreateOpen] = useState(false)

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        title="Grupos"
        action={
          <Button
            type="button"
            onClick={() => {
              setCreateOpen(true)
            }}
          >
            Criar grupo
          </Button>
        }
      />
      <InvitationList invitations={invitations} />
      {groups.length === 0 ? (
        <div className="flex flex-col items-start gap-3">
          <p>Você ainda não está em um grupo.</p>
          <Button
            type="button"
            onClick={() => {
              setCreateOpen(true)
            }}
          >
            Criar grupo
          </Button>
        </div>
      ) : (
        <ul className="flex flex-col gap-3">
          {groups.map((group) => (
            <li key={group.id}>
              <Link
                to="/grupos/$groupId"
                params={{ groupId: group.id }}
                className="flex items-center justify-between gap-3 rounded-xl bg-card p-4 ring-1 ring-foreground/10"
              >
                <span className="font-medium">{group.name}</span>
                {group.owner_id === me.id ? <Badge>Dono</Badge> : null}
              </Link>
            </li>
          ))}
        </ul>
      )}
      <CreateGroupDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  )
}
