import { useState } from 'react'
import { useQueryClient, useSuspenseQuery } from '@tanstack/react-query'

import { CardTitle } from '@/components/cards/card-title'
import { ConfirmDialog } from '@/components/confirm-dialog'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { invalidateBoard, reportBoardError } from '@/lib/api/invalidate'
import {
  acceptRequest,
  cancelRequest,
  confirmRequest,
  handoffsQueryOptions,
  rejectRequest,
} from '@/lib/api/requests'
import type { HandoffBring, HandoffReceive } from '@/lib/api/requests'
import { personName } from '@/lib/api/schemas'
import { sourceLabel } from '@/lib/display'

type ConfirmTarget = {
  id: string
  side: 'bring' | 'receive'
}

export function HandoffPage({ groupId }: { groupId: string }) {
  const queryClient = useQueryClient()
  const { data } = useSuspenseQuery(handoffsQueryOptions(groupId))
  const [cancelId, setCancelId] = useState<string | null>(null)
  const [confirmTarget, setConfirmTarget] = useState<ConfirmTarget | null>(null)
  const [pending, setPending] = useState(false)

  async function run(action: () => Promise<unknown>) {
    setPending(true)
    try {
      await action()
      await invalidateBoard(queryClient)
    } catch (error) {
      await reportBoardError(queryClient, error)
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <PageHeader title="Encontro" />
      <section className="flex flex-col gap-3">
        <h2 className="font-heading text-lg font-medium">Levar</h2>
        <p className="text-sm text-muted-foreground">
          Aceite os pedidos e leve as cartas no próximo encontro. Quem entrega e
          quem recebe confirmam no app.
        </p>
        {data.to_bring.length === 0 ? (
          <p>Nada para levar neste grupo.</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {data.to_bring.map((item) => (
              <BringRow
                key={item.id}
                item={item}
                pending={pending}
                onAccept={() => {
                  void run(() => acceptRequest(item.id))
                }}
                onReject={() => {
                  void run(() => rejectRequest(item.id))
                }}
                onConfirm={() => {
                  setConfirmTarget({ id: item.id, side: 'bring' })
                }}
              />
            ))}
          </ul>
        )}
      </section>
      <section className="flex flex-col gap-3">
        <h2 className="font-heading text-lg font-medium">Receber</h2>
        {data.to_receive.length === 0 ? (
          <p>Nada para receber neste grupo.</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {data.to_receive.map((item) => (
              <ReceiveRow
                key={item.id}
                item={item}
                pending={pending}
                onCancel={() => {
                  setCancelId(item.id)
                }}
                onConfirm={() => {
                  setConfirmTarget({ id: item.id, side: 'receive' })
                }}
              />
            ))}
          </ul>
        )}
      </section>
      <ConfirmDialog
        open={cancelId != null}
        onOpenChange={(open) => {
          if (!open) {
            setCancelId(null)
          }
        }}
        title="Cancelar pedido"
        description="O pedido é desfeito e a carta volta para onde estava."
        confirmLabel="Cancelar pedido"
        destructive
        pending={pending}
        onConfirm={() => {
          if (!cancelId) {
            return
          }

          const requestId = cancelId
          setCancelId(null)
          void run(() => cancelRequest(requestId))
        }}
      />
      <ConfirmDialog
        open={confirmTarget != null}
        onOpenChange={(open) => {
          if (!open) {
            setConfirmTarget(null)
          }
        }}
        title={
          confirmTarget?.side === 'bring'
            ? 'Confirmar entrega'
            : 'Confirmar recebimento'
        }
        description={
          confirmTarget?.side === 'bring'
            ? 'Confirme só se você já entregou a carta. A carta só muda de mão quando a outra pessoa também confirmar.'
            : 'Confirme só se a carta já está na sua mão. A carta só muda de mão quando a outra pessoa também confirmar. Trave no deck se não quiser que peçam.'
        }
        confirmLabel="Confirmar"
        pending={pending}
        onConfirm={() => {
          if (!confirmTarget) {
            return
          }

          const requestId = confirmTarget.id
          setConfirmTarget(null)
          void run(() => confirmRequest(requestId))
        }}
      />
    </div>
  )
}

function BringRow({
  item,
  pending,
  onAccept,
  onReject,
  onConfirm,
}: {
  item: HandoffBring
  pending: boolean
  onAccept: () => void
  onReject: () => void
  onConfirm: () => void
}) {
  return (
    <li className="flex flex-col gap-3 rounded-xl bg-card p-4 ring-1 ring-foreground/10">
      <div>
        <CardTitle
          namePt={item.catalog.name_pt}
          nameEn={item.catalog.name_en}
        />
        <p className="mt-1 text-sm break-all text-muted-foreground">
          Pedido de {personName(item.requester)}
        </p>
        <p className="text-sm text-muted-foreground">
          {item.target_deck.name}, {sourceLabel(item.source)}
        </p>
        <p className="text-sm">{bringStatus(item)}</p>
      </div>
      {item.status === 'pending_acceptance' ? (
        <div className="flex flex-wrap justify-end gap-2">
          <Button
            type="button"
            variant="outline"
            disabled={pending}
            onClick={onReject}
          >
            Recusar
          </Button>
          <Button type="button" disabled={pending} onClick={onAccept}>
            Aceitar
          </Button>
        </div>
      ) : item.holder_confirmed ? null : (
        <div className="flex flex-wrap justify-end gap-2">
          <Button type="button" disabled={pending} onClick={onConfirm}>
            Confirmar entrega
          </Button>
        </div>
      )}
    </li>
  )
}

function ReceiveRow({
  item,
  pending,
  onCancel,
  onConfirm,
}: {
  item: HandoffReceive
  pending: boolean
  onCancel: () => void
  onConfirm: () => void
}) {
  return (
    <li className="flex flex-col gap-3 rounded-xl bg-card p-4 ring-1 ring-foreground/10">
      <div>
        <CardTitle
          namePt={item.catalog.name_pt}
          nameEn={item.catalog.name_en}
        />
        <p className="mt-1 text-sm text-muted-foreground">
          {item.target_deck.name} · {sourceLabel(item.source)}
        </p>
        <p className="text-sm">{receiveStatus(item)}</p>
      </div>
      <div className="flex flex-wrap justify-end gap-2">
        <Button
          type="button"
          variant="outline"
          disabled={pending}
          onClick={onCancel}
        >
          Cancelar
        </Button>
        {item.status === 'awaiting_handoff' && !item.requester_confirmed ? (
          <Button type="button" disabled={pending} onClick={onConfirm}>
            Confirmar recebimento
          </Button>
        ) : null}
      </div>
    </li>
  )
}

function bringStatus(item: HandoffBring) {
  if (item.status === 'pending_acceptance') {
    return 'Aceite o pedido se você está com a carta e pode levá-la.'
  }

  if (item.holder_confirmed) {
    return `Você confirmou a entrega. Falta ${personName(item.requester)} confirmar o recebimento.`
  }

  if (item.requester_confirmed) {
    return `${personName(item.requester)} já confirmou o recebimento. Confirme a entrega.`
  }

  return 'Leve no encontro. Quem entrega e quem recebe confirmam no app.'
}

function receiveStatus(item: HandoffReceive) {
  if (item.status === 'pending_acceptance') {
    return `Esperando aceite de ${personName(item.holder)}.`
  }

  if (item.requester_confirmed) {
    return `Você confirmou o recebimento. Falta ${personName(item.holder)} confirmar a entrega.`
  }

  if (item.holder_confirmed) {
    return `${personName(item.holder)} confirmou a entrega. Confirme se a carta está na sua mão.`
  }

  return 'Esperando a carta. Quem entrega e quem recebe confirmam no app.'
}
