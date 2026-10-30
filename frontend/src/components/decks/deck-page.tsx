import { useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import {
  useMutation,
  useQuery,
  useQueryClient,
  useSuspenseQuery,
} from '@tanstack/react-query'
import { Link, useNavigate } from '@tanstack/react-router'
import { Loader2Icon } from 'lucide-react'
import { Controller, useForm } from 'react-hook-form'
import { z } from 'zod'

import { CardThumb } from '@/components/cards/card-thumb'
import { CardTitle } from '@/components/cards/card-title'
import { ManaCost } from '@/components/cards/mana-cost'
import { ColorIdentity } from '@/components/cards/color-identity'
import { CatalogSearch } from '@/components/copies/catalog-search'
import { ConfirmDialog } from '@/components/confirm-dialog'
import { PageHeader } from '@/components/layout/page-header'
import { ActionMenu } from '@/components/ui/action-menu'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { meQueryOptions } from '@/lib/api/auth'
import type { CatalogCard } from '@/lib/api/catalog'
import { refreshCopyPrice, shareCopy } from '@/lib/api/copies'
import {
  addDeckCopies,
  deckCopiesInputSchema,
  deckQueryOptions,
  deleteDeck,
  listDecks,
  lockDeckCard,
  moveDeckCard,
  returnDeckCard,
  setCommanders,
  unlockDeckCard,
  updateDeck,
  updateDeckInputSchema,
} from '@/lib/api/decks'
import type {
  DeckCard,
  DeckDetail,
  DeckWarning,
  UpdateDeckInput,
} from '@/lib/api/decks'
import { groupsQueryOptions } from '@/lib/api/groups'
import { invalidateBoard, reportBoardError } from '@/lib/api/invalidate'
import { acceptRequest, rejectRequest } from '@/lib/api/requests'
import { copyActionLabel, planDeckActions } from '@/lib/copy-actions'
import type { CopyAction } from '@/lib/copy-actions'
import {
  deckFormatLabel,
  deckFormats,
  formatColorIdentity,
} from '@/lib/display'
import { formatCents, formatCopyPrice } from '@/lib/money'

const countCodes = ['deck_over_100', 'deck_under_100']
const budgetCodes = ['budget_main', 'budget_commanders', 'missing_price']
const listCodes = [
  'duplicate_name',
  'color_identity',
  'banned',
  'commander_illegal',
]
const cardCodes = ['missing_price', ...listCodes]

function warningMessages(
  warnings: Array<DeckWarning>,
  codes: Array<string>,
  cardCopyId?: string,
) {
  return warnings
    .filter((warning) => {
      if (!codes.includes(warning.code)) {
        return false
      }

      if (cardCopyId === undefined) {
        return true
      }

      return warning.card_copy_id === cardCopyId
    })
    .map((warning) => warning.message)
}

export function DeckPage({
  groupId,
  deckId,
}: {
  groupId: string
  deckId: string
}) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: me } = useSuspenseQuery(meQueryOptions())
  const { data: deck } = useSuspenseQuery(deckQueryOptions(deckId))
  const isOwner = deck.owner_id === me.id
  const [editOpen, setEditOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [addOpen, setAddOpen] = useState(false)
  const [shareId, setShareId] = useState<string | null>(null)
  const [returnId, setReturnId] = useState<string | null>(null)
  const [moveId, setMoveId] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const commanders = deck.cards.filter((card) => card.role === 'commander')
  const main = deck.cards.filter((card) => card.role === 'main')
  const missingPrice = deck.warnings.some(
    (warning) => warning.code === 'missing_price',
  )

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

  function toggleCommander(cardCopyId: string) {
    const current = commanders.map((card) => card.card_copy_id)
    const next = current.includes(cardCopyId)
      ? current.filter((id) => id !== cardCopyId)
      : [...current, cardCopyId]
    void run(`commander:${cardCopyId}`, () => setCommanders(deck.id, next))
  }

  function perform(card: DeckCard, action: CopyAction) {
    if (action === 'share') {
      setShareId(card.card_copy_id)
      return
    }

    if (action === 'return') {
      setReturnId(card.card_copy_id)
      return
    }

    if (action === 'move') {
      setMoveId(card.card_copy_id)
      return
    }

    if (action === 'refresh') {
      void run(`refresh:${card.card_copy_id}`, () =>
        refreshCopyPrice(card.card_copy_id),
      )
      return
    }

    if (action === 'accept' && card.open_request) {
      const requestId = card.open_request.id
      void run(`accept:${card.card_copy_id}`, () => acceptRequest(requestId))
      return
    }

    if (action === 'reject' && card.open_request) {
      const requestId = card.open_request.id
      void run(`reject:${card.card_copy_id}`, () => rejectRequest(requestId))
      return
    }

    if (action === 'lock') {
      void run(`lock:${card.card_copy_id}`, () =>
        lockDeckCard(deck.id, card.card_copy_id),
      )
      return
    }

    if (action === 'unlock') {
      void run(`unlock:${card.card_copy_id}`, () =>
        unlockDeckCard(deck.id, card.card_copy_id),
      )
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={deck.name}
        description={
          <span className="inline-flex flex-wrap items-center gap-x-3 gap-y-1">
            <span>{deckFormatLabel(deck.format)}</span>
            <ColorIdentity
              colors={deck.color_identity}
              name={deck.color_identity_name}
            />
          </span>
        }
        action={
          isOwner ? (
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setEditOpen(true)
                }}
              >
                Editar
              </Button>
              <Button
                type="button"
                variant="destructive"
                onClick={() => {
                  setDeleteOpen(true)
                }}
              >
                Apagar
              </Button>
            </div>
          ) : null
        }
      />
      <section className="flex flex-col gap-1">
        <h2 className="font-heading text-lg font-medium">Contagem</h2>
        <p>{deck.card_count} de 100</p>
        <WarningLines messages={warningMessages(deck.warnings, countCodes)} />
      </section>
      <Budget deck={deck} missingPrice={missingPrice} />
      <WarningLines messages={warningMessages(deck.warnings, listCodes)} />
      {isOwner ? (
        <Button
          type="button"
          className="w-fit"
          onClick={() => {
            setAddOpen(true)
          }}
        >
          Adicionar carta
        </Button>
      ) : null}
      {deck.cards.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Este deck ainda não tem cartas.{' '}
          <Link
            to="/grupos/$groupId"
            params={{ groupId }}
            search={{ destino: deck.id }}
            className="underline-offset-4 hover:underline"
          >
            Pegue uma carta livre da sua casa no bulk.
          </Link>
        </p>
      ) : null}
      <CardBlock
        title="Comandantes"
        cards={commanders}
        empty="Nenhum comandante."
        pairing={warningMessages(deck.warnings, ['commander_pairing'])}
        deck={deck}
        meId={me.id}
        isOwner={isOwner}
        busy={busy != null}
        onCommander={toggleCommander}
        onAction={perform}
      />
      <CardBlock
        title="Cartas"
        cards={main}
        empty="Nenhuma carta fora dos comandantes."
        pairing={[]}
        deck={deck}
        meId={me.id}
        isOwner={isOwner}
        busy={busy != null}
        onCommander={toggleCommander}
        onAction={perform}
      />
      <EditDeckDialog deck={deck} open={editOpen} onOpenChange={setEditOpen} />
      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Apagar deck"
        description="As cartas voltam para o bulk, livres, na casa de quem está com elas."
        confirmLabel="Apagar"
        destructive
        pending={busy != null}
        onConfirm={() => {
          void run('delete', async () => {
            await deleteDeck(deck.id)
            await navigate({
              to: '/grupos/$groupId/decks',
              params: { groupId },
            })
          })
        }}
      />
      <AddDeckCardDialog
        open={addOpen}
        onOpenChange={setAddOpen}
        deckId={deck.id}
      />
      <ShareFromDeckDialog
        copyId={shareId}
        groupId={groupId}
        onOpenChange={(open) => {
          if (!open) {
            setShareId(null)
          }
        }}
      />
      <ConfirmDialog
        open={returnId != null}
        onOpenChange={(open) => {
          if (!open) {
            setReturnId(null)
          }
        }}
        title="Devolver ao bulk"
        description="A carta sai do deck e volta a ficar livre na sua casa."
        confirmLabel="Devolver"
        pending={busy != null}
        onConfirm={() => {
          if (!returnId) {
            return
          }

          const cardCopyId = returnId
          setReturnId(null)
          void run(`return:${cardCopyId}`, () =>
            returnDeckCard(deck.id, cardCopyId),
          )
        }}
      />
      <DeckMoveDialog
        open={moveId != null}
        sourceDeckId={deck.id}
        pending={busy != null}
        onOpenChange={(open) => {
          if (!open) {
            setMoveId(null)
          }
        }}
        onMove={(targetDeckId) => {
          if (!moveId) {
            return
          }

          const cardCopyId = moveId
          setMoveId(null)
          void run(`move:${cardCopyId}`, () =>
            moveDeckCard(deck.id, cardCopyId, targetDeckId),
          )
        }}
      />
    </div>
  )
}

function Budget({
  deck,
  missingPrice,
}: {
  deck: DeckDetail
  missingPrice: boolean
}) {
  const caps = deck.format === 'commander_10'

  return (
    <section className="flex flex-col gap-1">
      <h2 className="font-heading text-lg font-medium">Orçamento</h2>
      <p>
        Cartas: {formatCents(deck.main_price_cents)}
        {caps ? ` de ${formatCents(1000)}` : null}
      </p>
      <p>
        Comandantes: {formatCents(deck.commander_price_cents)}
        {caps ? ` de ${formatCents(500)}` : null}
      </p>
      {missingPrice ? <p>Orçamento incompleto</p> : null}
      <WarningLines messages={warningMessages(deck.warnings, budgetCodes)} />
    </section>
  )
}

function WarningLines({ messages }: { messages: Array<string> }) {
  if (messages.length === 0) {
    return null
  }

  return (
    <ul className="flex flex-col gap-1 text-sm text-destructive">
      {messages.map((message, index) => (
        <li key={`${message}-${index}`}>{message}</li>
      ))}
    </ul>
  )
}

function CardBlock({
  title,
  cards,
  empty,
  pairing,
  deck,
  meId,
  isOwner,
  busy,
  onCommander,
  onAction,
}: {
  title: string
  cards: Array<DeckCard>
  empty: string
  pairing: Array<string>
  deck: DeckDetail
  meId: string
  isOwner: boolean
  busy: boolean
  onCommander: (cardCopyId: string) => void
  onAction: (card: DeckCard, action: CopyAction) => void
}) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="font-heading text-lg font-medium">{title}</h2>
      <WarningLines messages={pairing} />
      {cards.length === 0 ? (
        <p className="text-sm text-muted-foreground">{empty}</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {cards.map((card) => {
            const plan = planDeckActions(card, meId, isOwner)
            const cardWarnings = warningMessages(
              deck.warnings,
              cardCodes,
              card.card_copy_id,
            )

            return (
              <li
                key={card.card_copy_id}
                className="flex flex-col gap-3 rounded-xl bg-card p-4 ring-1 ring-foreground/10"
              >
                <div className="flex items-start gap-3">
                  <CardThumb url={card.catalog.image_url} />
                  <div className="flex min-w-0 flex-col gap-1">
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                      <CardTitle
                        namePt={card.catalog.name_pt}
                        nameEn={card.catalog.name_en}
                      />
                      <ManaCost cost={card.catalog.mana_cost} />
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {[
                        card.catalog.type_line,
                        formatColorIdentity(card.catalog.color_identity),
                        `Casa ${card.holder.nick}`,
                        formatCopyPrice(
                          card.price_cents,
                          card.catalog.is_basic,
                        ),
                      ]
                        .filter(Boolean)
                        .join(' · ')}
                    </p>
                    {card.catalog.partner_kind ? (
                      <p className="text-sm text-muted-foreground">
                        {card.catalog.partner_kind}
                      </p>
                    ) : null}
                    <Badge variant="secondary">
                      {card.locked ? 'Travada' : 'Destravada'}
                    </Badge>
                    <WarningLines messages={cardWarnings} />
                  </div>
                </div>
                {isOwner ? (
                  <div className="flex flex-wrap items-center justify-end gap-2">
                    {card.can_toggle_commander ? (
                      <Button
                        type="button"
                        variant="outline"
                        disabled={busy}
                        onClick={() => {
                          onCommander(card.card_copy_id)
                        }}
                      >
                        {card.role === 'commander'
                          ? 'Tirar de comandante'
                          : 'Marcar comandante'}
                      </Button>
                    ) : null}
                    {plan.buttons.slice(0, 1).map((action) => (
                      <Button
                        key={action}
                        type="button"
                        disabled={busy}
                        onClick={() => {
                          onAction(card, action)
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
                        disabled={busy}
                        onClick={() => {
                          onAction(card, action)
                        }}
                      >
                        {copyActionLabel[action]}
                      </Button>
                    ))}
                    <ActionMenu
                      items={plan.menu.map((action) => ({
                        id: action,
                        label: copyActionLabel[action],
                        onSelect: () => {
                          onAction(card, action)
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
    </section>
  )
}

function EditDeckDialog({
  deck,
  open,
  onOpenChange,
}: {
  deck: DeckDetail
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const queryClient = useQueryClient()
  const form = useForm<UpdateDeckInput>({
    resolver: zodResolver(updateDeckInputSchema),
    values: { name: deck.name, format: deck.format },
  })
  const mutation = useMutation({
    mutationFn: (values: UpdateDeckInput) => updateDeck(deck.id, values),
    onSuccess: async () => {
      await invalidateBoard(queryClient)
      onOpenChange(false)
    },
    onError: (error) => {
      void reportBoardError(queryClient, error)
    },
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange} title="Editar deck">
      <form
        className="flex flex-col gap-4"
        noValidate
        onSubmit={form.handleSubmit((values) => mutation.mutateAsync(values))}
      >
        <FieldGroup>
          <Controller
            name="name"
            control={form.control}
            render={({ field, fieldState }) => (
              <Field data-invalid={fieldState.invalid}>
                <FieldLabel htmlFor="edit-deck-name">Nome</FieldLabel>
                <Input
                  {...field}
                  id="edit-deck-name"
                  value={field.value ?? ''}
                  aria-invalid={fieldState.invalid}
                />
                {fieldState.invalid ? (
                  <FieldError errors={[fieldState.error]} />
                ) : null}
              </Field>
            )}
          />
          <Controller
            name="format"
            control={form.control}
            render={({ field, fieldState }) => (
              <Field data-invalid={fieldState.invalid}>
                <FieldLabel>Formato</FieldLabel>
                <div className="flex flex-col gap-2">
                  {deckFormats.map((format) => (
                    <label key={format.value} className="flex gap-2 text-sm">
                      <input
                        type="radio"
                        name="edit-format"
                        value={format.value}
                        checked={field.value === format.value}
                        onChange={() => {
                          field.onChange(format.value)
                        }}
                      />
                      <span>
                        {format.label}
                        <span className="block text-muted-foreground">
                          {format.hint}
                        </span>
                      </span>
                    </label>
                  ))}
                </div>
                {fieldState.invalid ? (
                  <FieldError errors={[fieldState.error]} />
                ) : null}
              </Field>
            )}
          />
        </FieldGroup>
        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? <Loader2Icon className="animate-spin" /> : null}
          Salvar
        </Button>
      </form>
    </Dialog>
  )
}

const quantityFormSchema = z.object({
  quantity: deckCopiesInputSchema.shape.quantity,
})

function AddDeckCardDialog({
  open,
  onOpenChange,
  deckId,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  deckId: string
}) {
  const queryClient = useQueryClient()
  const [card, setCard] = useState<CatalogCard | null>(null)
  const form = useForm<z.infer<typeof quantityFormSchema>>({
    resolver: zodResolver(quantityFormSchema),
    defaultValues: { quantity: 1 },
  })
  const mutation = useMutation({
    mutationFn: (quantity: number) =>
      addDeckCopies(deckId, {
        oracle_id: card?.oracle_id ?? '',
        quantity,
      }),
    onSuccess: async () => {
      await invalidateBoard(queryClient)
      setCard(null)
      form.reset({ quantity: 1 })
      onOpenChange(false)
    },
    onError: (error) => {
      void reportBoardError(queryClient, error)
    },
  })

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) {
          setCard(null)
        }

        onOpenChange(next)
      }}
      title="Adicionar ao deck"
      description="Se você já tem a carta livre no bulk, ela é travada neste deck. Se não, é cadastrada já aqui, travada, na sua casa."
    >
      {card ? (
        <form
          className="flex flex-col gap-4"
          noValidate
          onSubmit={form.handleSubmit((values) =>
            mutation.mutateAsync(values.quantity),
          )}
        >
          <CardTitle namePt={card.name_pt} nameEn={card.name_en} />
          <FieldGroup>
            <Controller
              name="quantity"
              control={form.control}
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor="deck-quantity">Quantidade</FieldLabel>
                  <Input
                    id="deck-quantity"
                    type="number"
                    min={1}
                    max={99}
                    step={1}
                    inputMode="numeric"
                    value={Number.isNaN(field.value) ? '' : field.value}
                    onChange={(event) => {
                      const raw = event.target.value
                      field.onChange(raw === '' ? Number.NaN : Number(raw))
                    }}
                    aria-invalid={fieldState.invalid}
                  />
                  {fieldState.invalid ? (
                    <FieldError errors={[fieldState.error]} />
                  ) : null}
                </Field>
              )}
            />
          </FieldGroup>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setCard(null)
              }}
            >
              Trocar
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? (
                <Loader2Icon className="animate-spin" />
              ) : null}
              Cadastrar
            </Button>
          </div>
        </form>
      ) : (
        <CatalogSearch deckId={deckId} onSelect={setCard} />
      )}
    </Dialog>
  )
}

function ShareFromDeckDialog({
  copyId,
  groupId,
  onOpenChange,
}: {
  copyId: string | null
  groupId: string
  onOpenChange: (open: boolean) => void
}) {
  const queryClient = useQueryClient()
  const groups = useQuery({
    ...groupsQueryOptions(),
    enabled: copyId != null,
  })
  const others = (groups.data ?? []).filter((group) => group.id !== groupId)
  const [pending, setPending] = useState(false)

  return (
    <Dialog
      open={copyId != null}
      onOpenChange={onOpenChange}
      title="Compartilhar"
      description="A carta está num deck e continua travada. O outro grupo passa a vê-la assim."
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
                disabled={pending || !copyId}
                onClick={() => {
                  if (!copyId) {
                    return
                  }

                  setPending(true)
                  void shareCopy(copyId, group.id)
                    .then(async () => {
                      await invalidateBoard(queryClient)
                      onOpenChange(false)
                    })
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

function DeckMoveDialog({
  open,
  sourceDeckId,
  pending,
  onOpenChange,
  onMove,
}: {
  open: boolean
  sourceDeckId: string
  pending: boolean
  onOpenChange: (open: boolean) => void
  onMove: (targetDeckId: string) => void
}) {
  const groups = useQuery({
    ...groupsQueryOptions(),
    enabled: open,
  })
  const destinations = useQuery({
    queryKey: [
      'deck-move-targets',
      sourceDeckId,
      (groups.data ?? []).map((group) => group.id).join('|'),
    ],
    enabled: open && groups.isSuccess,
    queryFn: async () => {
      const lists = await Promise.all(
        (groups.data ?? []).map(async (group) => {
          const decks = await listDecks(group.id)
          return decks
            .filter((deck) => deck.id !== sourceDeckId)
            .map((deck) => ({
              id: deck.id,
              label: `${group.name} · ${deck.name}`,
            }))
        }),
      )
      return lists.flat()
    },
  })

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title="Mover carta"
      description="Se esta carta é comandante, ela volta ao destino como carta comum. Marque comandante de novo se quiser."
    >
      {(destinations.data ?? []).length === 0 ? (
        <p className="text-sm text-muted-foreground">
          {destinations.isFetching
            ? 'Buscando decks…'
            : 'Você não tem outro deck.'}
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {(destinations.data ?? []).map((deck) => (
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
                {deck.label}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </Dialog>
  )
}
