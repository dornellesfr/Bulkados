import { useState } from 'react'
import {
  useQuery,
  useQueryClient,
  useSuspenseQuery,
} from '@tanstack/react-query'

import { CardTitle } from '@/components/cards/card-title'
import { ConfirmDialog } from '@/components/confirm-dialog'
import { RegisterCopyDialog } from '@/components/copies/register-copy-dialog'
import { CreateDeckDialog } from '@/components/decks/create-deck-dialog'
import { PageHeader } from '@/components/layout/page-header'
import { ActionMenu } from '@/components/ui/action-menu'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { NativeSelect } from '@/components/ui/native-select'
import { meQueryOptions } from '@/lib/api/auth'
import {
  copiesQueryOptions,
  deleteCopy,
  filterCopies,
  refreshCopyPrice,
  shareCopy,
} from '@/lib/api/copies'
import type { BulkSearch, Copy, CopyVisibility } from '@/lib/api/copies'
import {
  decksQueryOptions,
  listDecks,
  lockDeckCard,
  moveDeckCard,
  returnDeckCard,
  takeCopy,
  unlockDeckCard,
} from '@/lib/api/decks'
import { groupsQueryOptions } from '@/lib/api/groups'
import { invalidateBoard, reportBoardError } from '@/lib/api/invalidate'
import {
  acceptRequest,
  cancelRequest,
  rejectRequest,
  requestCopy,
} from '@/lib/api/requests'
import {
  copyActionLabel,
  copyStateText,
  planBulkActions,
} from '@/lib/copy-actions'
import type { CopyAction } from '@/lib/copy-actions'
import { formatColorIdentity } from '@/lib/display'
import { formatCopyPrice } from '@/lib/money'

const visibilityOptions: Array<{ value: CopyVisibility | ''; label: string }> =
  [
    { value: '', label: 'Todos os estados' },
    { value: 'available', label: 'Livre' },
    { value: 'reserved', label: 'Reservada' },
    { value: 'in_deck', label: 'No deck' },
    { value: 'in_use_elsewhere', label: 'Em uso em outro grupo' },
  ]

type PendingDeck = {
  copyId: string
  mode: 'take' | 'request'
}

export function BulkPage({
  groupId,
  search,
  onSearchChange,
}: {
  groupId: string
  search: BulkSearch
  onSearchChange: (search: BulkSearch) => void
}) {
  const queryClient = useQueryClient()
  const { data: me } = useSuspenseQuery(meQueryOptions())
  const { data: copies } = useSuspenseQuery(copiesQueryOptions(groupId))
  const { data: decks } = useSuspenseQuery(decksQueryOptions(groupId))
  const visible = filterCopies(copies, search)
  const [registerOpen, setRegisterOpen] = useState(false)
  const [shareTarget, setShareTarget] = useState<Copy | null>(null)
  const [removeTarget, setRemoveTarget] = useState<Copy | null>(null)
  const [cancelTarget, setCancelTarget] = useState<Copy | null>(null)
  const [returnTarget, setReturnTarget] = useState<Copy | null>(null)
  const [moveTarget, setMoveTarget] = useState<Copy | null>(null)
  const [choice, setChoice] = useState<PendingDeck | null>(null)
  const [createFor, setCreateFor] = useState<PendingDeck | null>(null)
  const [busy, setBusy] = useState<string | null>(null)

  async function run(key: string, action: () => Promise<unknown>) {
    setBusy(key)
    try {
      await action()
      await invalidateBoard(queryClient)
    } catch (error) {
      await reportBoardError(queryClient, error)
    } finally {
      setBusy(null)
    }
  }

  function bindDeck(copyId: string, mode: 'take' | 'request', deckId: string) {
    const key = `${mode}:${copyId}`
    void run(key, () =>
      mode === 'take' ? takeCopy(deckId, copyId) : requestCopy(deckId, copyId),
    )
  }

  function startDeckAction(copyId: string, mode: 'take' | 'request') {
    if (search.destino && decks.some((deck) => deck.id === search.destino)) {
      bindDeck(copyId, mode, search.destino)
      return
    }

    if (decks.length === 0) {
      setCreateFor({ copyId, mode })
      return
    }

    if (decks.length === 1) {
      bindDeck(copyId, mode, decks[0].id)
      return
    }

    setChoice({ copyId, mode })
  }

  function perform(copy: Copy, action: CopyAction) {
    if (action === 'take') {
      startDeckAction(copy.id, 'take')
      return
    }

    if (action === 'request') {
      startDeckAction(copy.id, 'request')
      return
    }

    if (action === 'share') {
      setShareTarget(copy)
      return
    }

    if (action === 'remove') {
      setRemoveTarget(copy)
      return
    }

    if (action === 'cancel') {
      setCancelTarget(copy)
      return
    }

    if (action === 'return') {
      setReturnTarget(copy)
      return
    }

    if (action === 'move') {
      setMoveTarget(copy)
      return
    }

    if (action === 'refresh') {
      void run(`refresh:${copy.id}`, () => refreshCopyPrice(copy.id))
      return
    }

    if (action === 'accept' && copy.open_request) {
      const requestId = copy.open_request.id
      void run(`accept:${copy.id}`, () => acceptRequest(requestId))
      return
    }

    if (action === 'reject' && copy.open_request) {
      const requestId = copy.open_request.id
      void run(`reject:${copy.id}`, () => rejectRequest(requestId))
      return
    }

    const deckId = copy.deck?.id

    if (!deckId) {
      return
    }

    if (action === 'lock') {
      void run(`lock:${copy.id}`, () => lockDeckCard(deckId, copy.id))
      return
    }

    if (action === 'unlock') {
      void run(`unlock:${copy.id}`, () => unlockDeckCard(deckId, copy.id))
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Bulk"
        action={
          <Button
            type="button"
            onClick={() => {
              setRegisterOpen(true)
            }}
          >
            Cadastrar carta
          </Button>
        }
      />
      <form
        className="flex flex-col gap-2 sm:flex-row"
        onSubmit={(event) => {
          event.preventDefault()
          const formData = new FormData(event.currentTarget)
          const q = String(formData.get('q') ?? '').trim()
          onSearchChange({
            ...search,
            ...(q ? { q } : { q: undefined }),
          })
        }}
      >
        <Input
          name="q"
          defaultValue={search.q ?? ''}
          placeholder="Filtrar por nome"
          aria-label="Filtrar por nome"
        />
        <NativeSelect
          aria-label="Estado"
          value={search.estado ?? ''}
          onChange={(event) => {
            const estado = event.target.value as CopyVisibility | ''
            onSearchChange({
              ...search,
              estado: estado || undefined,
            })
          }}
        >
          {visibilityOptions.map((option) => (
            <option key={option.label} value={option.value}>
              {option.label}
            </option>
          ))}
        </NativeSelect>
        <Button type="submit" variant="outline">
          Filtrar
        </Button>
      </form>
      {visible.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          {copies.length === 0
            ? 'Nenhuma carta neste grupo.'
            : 'Nenhuma carta com esse filtro.'}
        </p>
      ) : (
        <ul className="flex flex-col gap-3">
          {visible.map((copy) => {
            const plan = planBulkActions(copy, me.id)
            const state = copyStateText(copy)
            const showActions = plan.buttons.length > 0 || plan.menu.length > 0

            return (
              <li
                key={copy.id}
                className="flex flex-col gap-3 rounded-xl bg-card p-4 ring-1 ring-foreground/10"
              >
                <div className="flex flex-col gap-1">
                  <CardTitle
                    namePt={copy.catalog.name_pt}
                    nameEn={copy.catalog.name_en}
                  />
                  <p className="text-sm text-muted-foreground">
                    {[
                      copy.catalog.type_line,
                      formatColorIdentity(copy.catalog.color_identity),
                      `Casa ${copy.holder.nick}`,
                      formatCopyPrice(copy.price_cents, copy.catalog.is_basic),
                    ]
                      .filter(Boolean)
                      .join(' · ')}
                  </p>
                  <div className="flex flex-wrap items-center gap-2 text-sm">
                    <span>{state.label}</span>
                    {state.detail ? <span>{state.detail}</span> : null}
                    {state.badge ? (
                      <Badge variant="secondary">{state.badge}</Badge>
                    ) : null}
                  </div>
                </div>
                {showActions ? (
                  <div className="flex flex-wrap items-center justify-end gap-2">
                    {plan.buttons.slice(0, 1).map((action) => (
                      <Button
                        key={action}
                        type="button"
                        disabled={busy != null}
                        onClick={() => {
                          perform(copy, action)
                        }}
                      >
                        {copyActionLabel[action]}
                      </Button>
                    ))}
                    {plan.buttons.slice(1).map((action) => (
                      <Button
                        key={action}
                        type="button"
                        variant="outline"
                        disabled={busy != null}
                        onClick={() => {
                          perform(copy, action)
                        }}
                      >
                        {copyActionLabel[action]}
                      </Button>
                    ))}
                    <ActionMenu
                      items={plan.menu.map((action) => ({
                        id: action,
                        label: copyActionLabel[action],
                        destructive: action === 'remove',
                        onSelect: () => {
                          perform(copy, action)
                        },
                      }))}
                    />
                  </div>
                ) : null}
              </li>
            )
          })}
        </ul>
      )}
      <RegisterCopyDialog
        open={registerOpen}
        onOpenChange={setRegisterOpen}
        groupId={groupId}
        meId={me.id}
      />
      <ShareDialog
        copy={shareTarget}
        groupId={groupId}
        onOpenChange={(open) => {
          if (!open) {
            setShareTarget(null)
          }
        }}
        onShared={() => {
          setShareTarget(null)
          return invalidateBoard(queryClient)
        }}
      />
      <ConfirmDialog
        open={removeTarget != null}
        onOpenChange={(open) => {
          if (!open) {
            setRemoveTarget(null)
          }
        }}
        title="Remover carta"
        description="Isso apaga o registro em todos os grupos. Só faça isso se o papel saiu de circulação."
        confirmLabel="Remover"
        destructive
        pending={busy != null}
        onConfirm={() => {
          if (!removeTarget) {
            return
          }

          const copyId = removeTarget.id
          setRemoveTarget(null)
          void run(`remove:${copyId}`, () => deleteCopy(copyId))
        }}
      />
      <ConfirmDialog
        open={cancelTarget != null}
        onOpenChange={(open) => {
          if (!open) {
            setCancelTarget(null)
          }
        }}
        title="Cancelar pedido"
        description="O pedido é desfeito e a carta volta para onde estava."
        confirmLabel="Cancelar pedido"
        destructive
        pending={busy != null}
        onConfirm={() => {
          if (!cancelTarget?.open_request) {
            return
          }

          const requestId = cancelTarget.open_request.id
          const copyId = cancelTarget.id
          setCancelTarget(null)
          void run(`cancel:${copyId}`, () => cancelRequest(requestId))
        }}
      />
      <ConfirmDialog
        open={returnTarget != null}
        onOpenChange={(open) => {
          if (!open) {
            setReturnTarget(null)
          }
        }}
        title="Devolver ao bulk"
        description="A carta sai do deck e volta a ficar livre na sua casa."
        confirmLabel="Devolver"
        pending={busy != null}
        onConfirm={() => {
          const deckId = returnTarget?.deck?.id

          if (!returnTarget || !deckId) {
            return
          }

          const copyId = returnTarget.id
          setReturnTarget(null)
          void run(`return:${copyId}`, () => returnDeckCard(deckId, copyId))
        }}
      />
      <MoveDialog
        copy={moveTarget}
        onOpenChange={(open) => {
          if (!open) {
            setMoveTarget(null)
          }
        }}
        pending={busy != null}
        onMove={(targetDeckId) => {
          const deckId = moveTarget?.deck?.id

          if (!moveTarget || !deckId) {
            return
          }

          const copyId = moveTarget.id
          setMoveTarget(null)
          void run(`move:${copyId}`, () =>
            moveDeckCard(deckId, copyId, targetDeckId),
          )
        }}
      />
      <Dialog
        open={choice != null}
        onOpenChange={(open) => {
          if (!open) {
            setChoice(null)
          }
        }}
        title={
          choice?.mode === 'request' ? 'Solicitar para o deck' : 'Pegar no deck'
        }
      >
        <ul className="flex flex-col gap-2">
          {decks.map((deck) => (
            <li key={deck.id}>
              <Button
                type="button"
                variant="outline"
                className="w-full justify-start"
                onClick={() => {
                  if (choice) {
                    bindDeck(choice.copyId, choice.mode, deck.id)
                  }

                  setChoice(null)
                }}
              >
                {deck.name}
              </Button>
            </li>
          ))}
        </ul>
      </Dialog>
      <CreateDeckDialog
        open={createFor != null}
        onOpenChange={(open) => {
          if (!open) {
            setCreateFor(null)
          }
        }}
        groupId={groupId}
        onCreated={(deck) => {
          if (createFor) {
            bindDeck(createFor.copyId, createFor.mode, deck.id)
          }

          setCreateFor(null)
        }}
      />
    </div>
  )
}

function ShareDialog({
  copy,
  groupId,
  onOpenChange,
  onShared,
}: {
  copy: Copy | null
  groupId: string
  onOpenChange: (open: boolean) => void
  onShared: () => Promise<void>
}) {
  const { data: groups = [] } = useQuery({
    ...groupsQueryOptions(),
    enabled: copy != null,
  })
  const others = groups.filter((group) => group.id !== groupId)
  const staysLocked = copy?.visibility === 'in_deck'
  const [pending, setPending] = useState(false)
  const queryClient = useQueryClient()

  return (
    <Dialog
      open={copy != null}
      onOpenChange={onOpenChange}
      title="Compartilhar"
      description={
        staysLocked
          ? 'A carta está num deck e continua travada. O outro grupo passa a vê-la assim.'
          : 'A carta entra livre no grupo escolhido.'
      }
    >
      {others.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Você não está em outro grupo.
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {others.map((group) => (
            <li key={group.id}>
              <Button
                type="button"
                variant="outline"
                className="w-full justify-start"
                disabled={pending}
                onClick={() => {
                  if (!copy) {
                    return
                  }

                  setPending(true)
                  void shareCopy(copy.id, group.id)
                    .then(() => onShared())
                    .catch((error: unknown) =>
                      reportBoardError(queryClient, error),
                    )
                    .finally(() => {
                      setPending(false)
                    })
                }}
              >
                {group.name}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </Dialog>
  )
}

function MoveDialog({
  copy,
  onOpenChange,
  onMove,
  pending,
}: {
  copy: Copy | null
  onOpenChange: (open: boolean) => void
  onMove: (deckId: string) => void
  pending: boolean
}) {
  const groups = useQuery({
    ...groupsQueryOptions(),
    enabled: copy != null,
  })
  const deckQueries = useSuspenseSafeDecks(groups.data ?? [], copy != null)
  const options = deckQueries.filter((deck) => deck.id !== copy?.deck?.id)

  return (
    <Dialog
      open={copy != null}
      onOpenChange={onOpenChange}
      title="Mover carta"
      description="Se esta carta é comandante, ela volta ao destino como carta comum. Marque comandante de novo se quiser."
    >
      {options.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Você não tem outro deck.
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {options.map((deck) => (
            <li key={deck.id}>
              <Button
                type="button"
                variant="outline"
                className="w-full justify-start"
                disabled={pending}
                onClick={() => {
                  onMove(deck.id)
                }}
              >
                {deck.groupName} · {deck.name}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </Dialog>
  )
}

function useSuspenseSafeDecks(
  groups: Array<{ id: string; name: string }>,
  enabled: boolean,
) {
  const queries = useQuery({
    queryKey: [
      'move-decks',
      groups.map((group) => group.id).join('|'),
      enabled,
    ],
    enabled: enabled && groups.length > 0,
    queryFn: async () => {
      const lists = await Promise.all(
        groups.map(async (group) => {
          const decks = await listDecks(group.id)
          return decks.map((deck) => ({
            ...deck,
            groupName: group.name,
          }))
        }),
      )
      return lists.flat()
    },
  })

  return queries.data ?? []
}
