import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'

import { ConfirmDialog } from '@/components/confirm-dialog'
import { Button } from '@/components/ui/button'
import { acceptInvitation, declineInvitation } from '@/lib/api/groups'
import type { Invitation } from '@/lib/api/groups'
import { invalidateMembership, toastError } from '@/lib/api/invalidate'

export function InvitationList({
  invitations,
}: {
  invitations: Array<Invitation>
}) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [declineId, setDeclineId] = useState<string | null>(null)
  const declineTarget = invitations.find((item) => item.id === declineId)

  const accept = useMutation({
    mutationFn: acceptInvitation,
    onSuccess: async (_data, invitationId) => {
      const invitation = invitations.find((item) => item.id === invitationId)
      await invalidateMembership(queryClient)

      if (invitation) {
        await navigate({
          to: '/grupos/$groupId',
          params: { groupId: invitation.group.id },
        })
      }
    },
    onError: (error) => {
      toastError(error)
    },
  })

  const decline = useMutation({
    mutationFn: declineInvitation,
    onSuccess: async () => {
      setDeclineId(null)
      await invalidateMembership(queryClient)
    },
    onError: (error) => {
      toastError(error)
    },
  })

  if (invitations.length === 0) {
    return null
  }

  return (
    <section className="flex flex-col gap-3">
      <h2 className="font-heading text-lg font-medium">Convites</h2>
      <ul className="flex flex-col gap-3">
        {invitations.map((invitation) => (
          <li
            key={invitation.id}
            className="flex flex-col gap-3 rounded-xl bg-card p-4 ring-1 ring-foreground/10 sm:flex-row sm:items-center sm:justify-between"
          >
            <div>
              <p className="font-medium">{invitation.group.name}</p>
              <p className="text-sm text-muted-foreground">
                Convite de {invitation.invited_by.nick}
              </p>
            </div>
            <div className="flex gap-2">
              <Button
                type="button"
                disabled={accept.isPending}
                onClick={() => {
                  accept.mutate(invitation.id)
                }}
              >
                Aceitar
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setDeclineId(invitation.id)
                }}
              >
                Recusar
              </Button>
            </div>
          </li>
        ))}
      </ul>
      <ConfirmDialog
        open={declineTarget != null}
        onOpenChange={(open) => {
          if (!open) {
            setDeclineId(null)
          }
        }}
        title="Recusar convite"
        description={
          declineTarget
            ? `Recusar o convite para ${declineTarget.group.name}?`
            : null
        }
        confirmLabel="Recusar"
        destructive
        pending={decline.isPending}
        onConfirm={() => {
          if (declineTarget) {
            decline.mutate(declineTarget.id)
          }
        }}
      />
    </section>
  )
}
