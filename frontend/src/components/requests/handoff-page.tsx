import { useState } from 'react'
import { useQueryClient, useSuspenseQuery } from '@tanstack/react-query'

import { CardTitle } from '@/components/cards/card-title'
import { ConfirmDialog } from '@/components/confirm-dialog'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { invalidateBoard, reportBoardError } from '@/lib/api/invalidate'
import {
  cancelRequest,
  confirmRequest,
  handoffsQueryOptions,
} from '@/lib/api/requests'
import type { HandoffReceive } from '@/lib/api/requests'
import { sourceLabel } from '@/lib/display'

export function HandoffPage({ groupId }: { groupId: string }) {
  const queryClient = useQueryClient()
  const { data } = useSuspenseQuery(handoffsQueryOptions(groupId))
  const [cancelId, setCancelId] = useState<string | null>(null)
  const [confirmId, setConfirmId] = useState<string | null>(null)
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
          Leve estas cartas no próximo encontro. Quem pediu confirma no app
          quando o papel estiver na mão dela.
        </p>
        {data.to_bring.length === 0 ? (
          <p>Nada para levar neste grupo.</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {data.to_bring.map((item) => (
              <li
                key={item.id}
                className="rounded-xl bg-card p-4 ring-1 ring-foreground/10"
              >
                <CardTitle
                  namePt={item.catalog.name_pt}
                  nameEn={item.catalog.name_en}
                />
                <p className="mt-1 text-sm text-muted-foreground">
                  {item.requester.nick} · {item.target_deck.name} ·{' '}
                  {sourceLabel(item.source)}
                </p>
              </li>
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
                  setConfirmId(item.id)
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
        open={confirmId != null}
        onOpenChange={(open) => {
          if (!open) {
            setConfirmId(null)
          }
        }}
        title="Confirmar recebimento"
        description="Confirme só se a carta já está na sua mão. A casa passa a ser você e ela entra no deck travada."
        confirmLabel="Confirmar"
        pending={pending}
        onConfirm={() => {
          if (!confirmId) {
            return
          }

          const requestId = confirmId
          setConfirmId(null)
          void run(() => confirmRequest(requestId))
        }}
      />
    </div>
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
        <p className="text-sm">
          {item.status === 'pending_acceptance'
            ? `Esperando aceite de ${item.holder.nick}`
            : 'Esperando a carta'}
        </p>
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
        {item.status === 'awaiting_handoff' ? (
          <Button type="button" disabled={pending} onClick={onConfirm}>
            Confirmar
          </Button>
        ) : null}
      </div>
    </li>
  )
}
