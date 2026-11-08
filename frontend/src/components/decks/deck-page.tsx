import { useState } from 'react'
import type { ReactNode } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import {
  useMutation,
  useQueryClient,
  useSuspenseQuery,
} from '@tanstack/react-query'
import { Link, useNavigate } from '@tanstack/react-router'
import {
  AlertTriangleIcon,
  ArrowLeftIcon,
  BellRingIcon,
  ChevronRightIcon,
  ListChecksIcon,
  Loader2Icon,
  LockIcon,
  LockOpenIcon,
  PencilIcon,
  PlusIcon,
  Trash2Icon,
} from 'lucide-react'
import { Controller, useForm } from 'react-hook-form'
import { z } from 'zod'

import { CardTitle } from '@/components/cards/card-title'
import { ColorIdentity } from '@/components/cards/color-identity'
import { CatalogSearch } from '@/components/copies/catalog-search'
import { ConfirmDialog } from '@/components/confirm-dialog'
import { DeckBulkDialog } from '@/components/decks/deck-bulk-dialog'
import { DeckCardDialog } from '@/components/decks/deck-card-dialog'
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
import { refreshCopyPrice } from '@/lib/api/copies'
import {
  addDeckCopies,
  deckCopiesInputSchema,
  deckQueryOptions,
  deleteDeck,
  lockDeckCard,
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
import { invalidateBoard, reportBoardError } from '@/lib/api/invalidate'
import { acceptRequest, rejectRequest } from '@/lib/api/requests'
import {
  deckBudgetCapCents,
  deckCategoryLabel,
  groupDeckCards,
  splitDeckColumns,
} from '@/lib/deck-view'
import type { DeckCardCategory } from '@/lib/deck-view'
import { deckFormatLabel, deckFormats } from '@/lib/display'
import { formatCents, formatCopyPrice } from '@/lib/money'
import { cn } from '@/lib/utils'

const warningTitles: Record<string, string> = {
  deck_under_100: 'Tamanho do deck',
  deck_over_100: 'Tamanho do deck',
  duplicate_name: 'Carta repetida',
  color_identity: 'Fora da identidade de cor',
  banned: 'Carta banida no Commander',
  commander_illegal: 'Comandante inválido',
  commander_pairing: 'Dupla de comandantes inválida',
  missing_price: 'Preço desconhecido',
  budget_main: 'Teto de preço das cartas',
  budget_commanders: 'Teto de preço dos comandantes',
}

function cardDisplayName(card: DeckCard) {
  return card.catalog.name_pt ?? card.catalog.name_en
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
  const [bulkOpen, setBulkOpen] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [returnId, setReturnId] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const selectedCard =
    deck.cards.find((card) => card.card_copy_id === selectedId) ?? null

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

  function toggleCommander(card: DeckCard) {
    const current = deck.cards
      .filter((item) => item.role === 'commander')
      .map((item) => item.card_copy_id)
    const next = current.includes(card.card_copy_id)
      ? current.filter((id) => id !== card.card_copy_id)
      : [...current, card.card_copy_id]
    void run(`commander:${card.card_copy_id}`, () =>
      setCommanders(deck.id, next),
    )
  }

  function toggleLock(card: DeckCard) {
    void run(`lock:${card.card_copy_id}`, () =>
      card.locked
        ? unlockDeckCard(deck.id, card.card_copy_id)
        : lockDeckCard(deck.id, card.card_copy_id),
    )
  }

  function refresh(card: DeckCard) {
    void run(`refresh:${card.card_copy_id}`, () =>
      refreshCopyPrice(card.card_copy_id),
    )
  }

  function accept(card: DeckCard) {
    if (!card.open_request) {
      return
    }

    const requestId = card.open_request.id
    void run(`accept:${card.card_copy_id}`, () => acceptRequest(requestId))
  }

  function reject(card: DeckCard) {
    if (!card.open_request) {
      return
    }

    const requestId = card.open_request.id
    void run(`reject:${card.card_copy_id}`, () => rejectRequest(requestId))
  }

  function requestReturn(card: DeckCard) {
    setSelectedId(null)
    setReturnId(card.card_copy_id)
  }

  return (
    <div className="flex flex-col gap-8">
      <DeckHero
        deck={deck}
        groupId={groupId}
        isOwner={isOwner}
        onEdit={() => {
          setEditOpen(true)
        }}
        onDelete={() => {
          setDeleteOpen(true)
        }}
        onBulk={() => {
          setBulkOpen(true)
        }}
      />
      <DeckSummary deck={deck} />
      <DeckWarnings deck={deck} />
      <DeckCards
        deck={deck}
        groupId={groupId}
        isOwner={isOwner}
        busyKey={busy}
        onAdd={() => {
          setAddOpen(true)
        }}
        onOpen={(card) => {
          setSelectedId(card.card_copy_id)
        }}
        onToggleLock={toggleLock}
      />
      <EditDeckDialog deck={deck} open={editOpen} onOpenChange={setEditOpen} />
      <DeckBulkDialog deck={deck} open={bulkOpen} onOpenChange={setBulkOpen} />
      <DeckCardDialog
        card={selectedCard}
        meId={me.id}
        isOwner={isOwner}
        busy={busy != null}
        busyKey={busy}
        onOpenChange={(open) => {
          if (!open) {
            setSelectedId(null)
          }
        }}
        onReturn={requestReturn}
        onToggleCommander={toggleCommander}
        onToggleLock={toggleLock}
        onRefresh={refresh}
        onAccept={accept}
        onReject={reject}
      />
      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Apagar deck?"
        description="Você realmente deseja apagar o deck? As cartas voltam para o bulk, livres, na casa de quem está com elas, inclusive as travadas."
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
      <ConfirmDialog
        open={returnId != null}
        onOpenChange={(open) => {
          if (!open) {
            setReturnId(null)
          }
        }}
        title="Remover do deck"
        description="A carta sai do deck e volta a ficar livre na sua casa."
        confirmLabel="Remover"
        destructive
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
      <AddDeckCardDialog
        open={addOpen}
        onOpenChange={setAddOpen}
        deckId={deck.id}
      />
    </div>
  )
}

function DeckHero({
  deck,
  groupId,
  isOwner,
  onEdit,
  onDelete,
  onBulk,
}: {
  deck: DeckDetail
  groupId: string
  isOwner: boolean
  onEdit: () => void
  onDelete: () => void
  onBulk: () => void
}) {
  const commanders = deck.cards.filter((card) => card.role === 'commander')
  const images = commanders
    .map((card) => card.catalog.image_url)
    .filter((url): url is string => url != null)
    .slice(0, 2)
  const title =
    commanders.length === 0
      ? deck.name
      : commanders
          .map((card) => card.catalog.name_pt ?? card.catalog.name_en)
          .join(' + ')

  return (
    <section className="relative isolate flex min-h-56 overflow-hidden rounded-2xl bg-muted ring-1 ring-foreground/10 sm:min-h-72">
      <div className="absolute inset-0" aria-hidden>
        {images.length === 0 ? (
          <div className="h-full w-full bg-gradient-to-br from-primary/30 via-muted to-background" />
        ) : (
          <div
            className={cn(
              'h-full',
              images.length > 1 ? 'grid grid-cols-2' : null,
            )}
          >
            {images.map((url, index) => (
              <img
                key={`${url}-${index}`}
                src={url}
                alt=""
                className="h-full w-full scale-105 object-cover blur-lg"
              />
            ))}
          </div>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/50 to-black/20" />
      </div>
      <div className="relative z-10 flex w-full flex-col justify-between gap-8 p-5 sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <Button
            asChild
            variant="ghost"
            size="icon"
            className="text-white/80 hover:bg-black/30 hover:text-white"
          >
            <Link
              to="/grupos/$groupId/decks"
              params={{ groupId }}
              aria-label="Voltar para decks"
              title="Voltar para decks"
            >
              <ArrowLeftIcon />
            </Link>
          </Button>
          {isOwner ? (
            <div className="flex flex-wrap justify-end gap-2">
              <HeroAction onClick={onEdit}>
                <PencilIcon />
                Editar
              </HeroAction>
              <HeroAction onClick={onBulk}>
                <ListChecksIcon />
                Editar em bulk
              </HeroAction>
              <HeroAction destructive onClick={onDelete}>
                <Trash2Icon />
                Apagar
              </HeroAction>
            </div>
          ) : null}
        </div>
        <div className="mt-auto max-w-3xl">
          {commanders.length === 0 ? (
            <p className="text-xs font-medium tracking-[0.24em] text-white/70 uppercase">
              Sem comandante
            </p>
          ) : null}
          <h1 className="font-heading text-4xl leading-tight font-medium text-white drop-shadow-md sm:text-5xl">
            {title}
          </h1>
        </div>
      </div>
    </section>
  )
}

function HeroAction({
  children,
  destructive = false,
  onClick,
}: {
  children: ReactNode
  destructive?: boolean
  onClick: () => void
}) {
  return (
    <Button
      type="button"
      variant="outline"
      className={cn(
        'border-white/25 bg-black/30 text-white hover:bg-black/50 hover:text-white',
        destructive &&
          'border-red-300/30 text-red-100 hover:bg-red-950/70 hover:text-red-50',
      )}
      onClick={onClick}
    >
      {children}
    </Button>
  )
}

function DeckSummary({ deck }: { deck: DeckDetail }) {
  const cap = deckBudgetCapCents(deck.format)

  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <span className="font-medium">{deckFormatLabel(deck.format)}</span>
        {deck.color_identity !== null ? (
          <>
            <span aria-hidden className="text-muted-foreground">
              ·
            </span>
            <ColorIdentity
              colors={deck.color_identity}
              name={deck.color_identity_name}
            />
          </>
        ) : null}
        <span aria-hidden className="text-muted-foreground">
          ·
        </span>
        <span className="text-muted-foreground">
          {deck.card_count} de 100 cartas
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-sm">
        <span>
          <span className="text-muted-foreground">Total das cartas </span>
          <span className="font-medium">
            {formatCents(deck.main_price_cents)}
          </span>
        </span>
        {cap != null ? (
          <span>
            <span className="text-muted-foreground">Pode chegar a </span>
            <span className="font-medium">{formatCents(cap)}</span>
          </span>
        ) : null}
      </div>
    </section>
  )
}

function DeckWarnings({ deck }: { deck: DeckDetail }) {
  const [open, setOpen] = useState(false)

  if (deck.warnings.length === 0) {
    return null
  }

  const count = deck.warnings.length

  return (
    <>
      <button
        type="button"
        className="flex w-full cursor-pointer items-center gap-3 rounded-xl bg-destructive/10 px-4 py-3 text-left text-destructive ring-1 ring-destructive/25 transition-colors outline-none hover:bg-destructive/15 focus-visible:ring-3 focus-visible:ring-ring/50"
        onClick={() => {
          setOpen(true)
        }}
      >
        <AlertTriangleIcon className="size-5 shrink-0" />
        <span className="min-w-0 flex-1">
          <span className="block font-medium">Deck fora das regras</span>
          <span className="block text-sm text-destructive/80">
            {count === 1 ? '1 aviso' : `${count} avisos`} · clique para ver os
            detalhes
          </span>
        </span>
        <ChevronRightIcon className="size-4 shrink-0" />
      </button>
      <Dialog
        open={open}
        onOpenChange={setOpen}
        title="Avisos do deck"
        description="O deck está fora das regras do formato. Estes avisos não impedem editar o deck."
      >
        <ul className="flex flex-col divide-y divide-foreground/10">
          {deck.warnings.map((warning, index) => (
            <WarningItem
              key={`${warning.code}-${warning.card_copy_id ?? index}`}
              warning={warning}
              deck={deck}
            />
          ))}
        </ul>
      </Dialog>
    </>
  )
}

function WarningItem({
  warning,
  deck,
}: {
  warning: DeckWarning
  deck: DeckDetail
}) {
  const card =
    deck.cards.find((item) => item.card_copy_id === warning.card_copy_id) ??
    null
  const commanders =
    warning.code === 'budget_commanders'
      ? deck.cards.filter((item) => item.role === 'commander')
      : []

  return (
    <li className="flex gap-3 py-3 first:pt-0 last:pb-0">
      <AlertTriangleIcon className="mt-0.5 size-4 shrink-0 text-destructive" />
      <div className="min-w-0 flex-1">
        <p className="font-medium">
          {warningTitles[warning.code] ?? 'Aviso do deck'}
        </p>
        <p className="text-sm text-muted-foreground">{warning.message}</p>
        {card ? (
          <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
            <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium">
              {card.role === 'commander' ? 'Comandante' : 'Carta'}
            </span>
            <span className="font-medium">{cardDisplayName(card)}</span>
            <span className="text-muted-foreground tabular-nums">
              {formatCopyPrice(card.price_cents, card.catalog.is_basic)}
            </span>
          </div>
        ) : null}
        {commanders.length > 0 ? (
          <ul className="mt-2 flex flex-col gap-1 text-sm">
            {commanders.map((commander) => (
              <li
                key={commander.card_copy_id}
                className="flex items-center justify-between gap-3"
              >
                <span className="truncate">{cardDisplayName(commander)}</span>
                <span className="shrink-0 text-muted-foreground tabular-nums">
                  {formatCopyPrice(
                    commander.price_cents,
                    commander.catalog.is_basic,
                  )}
                </span>
              </li>
            ))}
            <li className="flex items-center justify-between gap-3 border-t border-foreground/10 pt-1 font-medium">
              <span>Soma dos comandantes</span>
              <span className="tabular-nums">
                {formatCents(deck.commander_price_cents)}
              </span>
            </li>
          </ul>
        ) : null}
        {warning.code === 'budget_main' ? (
          <p className="mt-2 text-sm">
            <span className="text-muted-foreground">
              Soma atual das cartas (sem comandantes):{' '}
            </span>
            <span className="font-medium tabular-nums">
              {formatCents(deck.main_price_cents)}
            </span>
          </p>
        ) : null}
      </div>
    </li>
  )
}

function DeckCards({
  deck,
  groupId,
  isOwner,
  busyKey,
  onAdd,
  onOpen,
  onToggleLock,
}: {
  deck: DeckDetail
  groupId: string
  isOwner: boolean
  busyKey: string | null
  onAdd: () => void
  onOpen: (card: DeckCard) => void
  onToggleLock: (card: DeckCard) => void
}) {
  const sections = groupDeckCards(deck.cards)
  const columns = splitDeckColumns(sections)

  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-heading text-lg font-medium">Cartas</h2>
        {isOwner ? (
          <Button type="button" variant="outline" size="sm" onClick={onAdd}>
            <PlusIcon />
            Adicionar carta
          </Button>
        ) : null}
      </div>
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
      ) : (
        <div className="grid items-start gap-x-8 gap-y-6 lg:grid-cols-2">
          {columns.map((column, index) => (
            <div key={index} className="flex flex-col gap-6">
              {column.map((section) => (
                <CardSection
                  key={section.category}
                  category={section.category}
                  cards={section.cards}
                  isOwner={isOwner}
                  busyKey={busyKey}
                  onOpen={onOpen}
                  onToggleLock={onToggleLock}
                />
              ))}
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

function CardSection({
  category,
  cards,
  isOwner,
  busyKey,
  onOpen,
  onToggleLock,
}: {
  category: DeckCardCategory
  cards: Array<DeckCard>
  isOwner: boolean
  busyKey: string | null
  onOpen: (card: DeckCard) => void
  onToggleLock: (card: DeckCard) => void
}) {
  return (
    <section className="flex flex-col gap-1">
      <h3 className="flex items-baseline justify-between gap-3 border-b border-foreground/10 pb-1 text-xs font-medium tracking-[0.18em] text-muted-foreground uppercase">
        <span>{deckCategoryLabel(category, cards.length)}</span>
        <span className="tabular-nums">{cards.length}</span>
      </h3>
      <ul className="flex flex-col">
        {cards.map((card) => (
          <DeckCardRow
            key={card.card_copy_id}
            card={card}
            isOwner={isOwner}
            busy={busyKey != null}
            lockPending={busyKey === `lock:${card.card_copy_id}`}
            onOpen={onOpen}
            onToggleLock={onToggleLock}
          />
        ))}
      </ul>
    </section>
  )
}

function DeckCardRow({
  card,
  isOwner,
  busy,
  lockPending,
  onOpen,
  onToggleLock,
}: {
  card: DeckCard
  isOwner: boolean
  busy: boolean
  lockPending: boolean
  onOpen: (card: DeckCard) => void
  onToggleLock: (card: DeckCard) => void
}) {
  const name = card.catalog.name_pt ?? card.catalog.name_en
  const pending = card.open_request
  const pendingText = pending
    ? `Pedido de ${pending.requester.first_name} ${pending.requester.last_name}`
    : null

  return (
    <li>
      <div className="group flex items-center gap-1 rounded-lg pr-1 hover:bg-muted/70">
        {isOwner ? (
          <Button
            type="button"
            variant="ghost"
            size="icon-xs"
            className={cn(
              'shrink-0',
              card.locked
                ? 'text-amber-700 hover:text-amber-800 dark:text-amber-300'
                : 'text-muted-foreground',
            )}
            title={card.locked ? 'Destravar' : 'Travar para o deck'}
            aria-label={card.locked ? 'Destravar' : 'Travar para o deck'}
            disabled={busy || pending != null}
            onClick={() => {
              onToggleLock(card)
            }}
          >
            {lockPending ? (
              <Loader2Icon className="animate-spin" />
            ) : card.locked ? (
              <LockIcon />
            ) : (
              <LockOpenIcon />
            )}
          </Button>
        ) : (
          <span className="size-6 shrink-0" />
        )}
        <button
          type="button"
          className="flex min-w-0 flex-1 cursor-pointer items-center gap-2 rounded-md py-1.5 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring"
          onClick={() => {
            onOpen(card)
          }}
        >
          <span
            className={cn(
              'flex size-5 shrink-0 items-center justify-center',
              pending ? 'text-amber-600 dark:text-amber-300' : null,
            )}
            title={pendingText ?? undefined}
          >
            {pending ? <BellRingIcon className="size-4" /> : null}
          </span>
          <span className="min-w-0 flex-1 truncate">{name}</span>
          <span className="shrink-0 text-sm text-muted-foreground tabular-nums">
            {formatCopyPrice(card.price_cents, card.catalog.is_basic)}
          </span>
        </button>
      </div>
    </li>
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
      description="Se você já tem a carta livre no bulk, ela entra neste deck. Se não, é cadastrada já aqui, na sua casa. Ela não fica travada."
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
