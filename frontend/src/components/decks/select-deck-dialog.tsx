import { useEffect, useRef, useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2Icon } from 'lucide-react'
import { Controller, useForm } from 'react-hook-form'

import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import type { Copy } from '@/lib/api/copies'
import {
  createDeck,
  createDeckInputSchema,
  deckQueryOptions,
  moveDeckCard,
  takeCopy,
} from '@/lib/api/decks'
import type { CreateDeckInput, DeckSummary } from '@/lib/api/decks'
import { requestCopy } from '@/lib/api/requests'
import { invalidateBoard, toastError } from '@/lib/api/invalidate'
import { cardsOutsideIdentity, commanderSeat } from '@/lib/commander-seat'
import type { CommanderFacts } from '@/lib/commander-seat'
import { deckFormatLabel, deckFormats } from '@/lib/display'
import { cn } from '@/lib/utils'

export type DeckMode = 'take' | 'request' | 'move'

type Step = 'choose' | 'create' | 'existing'

export function SelectDeckDialog({
  open,
  onOpenChange,
  copy,
  mode,
  fromDeckId,
  groupId,
  decks,
  preferredDeckId,
  onDone,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  copy: Copy | null
  mode: DeckMode
  fromDeckId?: string
  groupId?: string
  decks: Array<DeckSummary>
  preferredDeckId?: string
  onDone: () => Promise<void>
}) {
  const queryClient = useQueryClient()
  const [step, setStep] = useState<Step>('choose')
  const [deckId, setDeckId] = useState<string | null>(null)
  const [asCommander, setAsCommander] = useState(false)
  const [createdId, setCreatedId] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const wasOpen = useRef(false)
  const allowCommander = mode !== 'request'
  const selected = decks.find((deck) => deck.id === deckId) ?? null
  const cardFacts = copy ? factsFromCopy(copy) : null
  const commanderFacts = selected
    ? selected.commanders.map(factsFromCommander)
    : []
  const pairing =
    cardFacts && selected
      ? commanderSeat(cardFacts, commanderFacts)
      : { allowed: false, reason: null as string | null }
  const detail = useQuery({
    ...deckQueryOptions(deckId ?? 'pending'),
    enabled:
      open &&
      step === 'existing' &&
      allowCommander &&
      deckId != null &&
      pairing.allowed,
  })
  const colorReason =
    detail.data && cardFacts
      ? cardsOutsideIdentity(
          [
            ...detail.data.cards
              .filter((card) => card.role === 'commander')
              .map((card) => card.catalog.color_identity),
            copy?.catalog.color_identity ?? [],
          ],
          detail.data.cards
            .filter((card) => card.role === 'main')
            .map((card) => ({
              nameEn: card.catalog.name_en,
              colorIdentity: card.catalog.color_identity,
            })),
        )
      : null
  const checkingColors = pairing.allowed && !detail.isFetched
  const commanderAllowed =
    pairing.allowed && detail.isSuccess && colorReason == null
  const commanderReason = commanderAllowed
    ? null
    : (colorReason ??
      (detail.isError
        ? 'Não foi possível conferir as cores deste deck.'
        : pairing.reason))

  useEffect(() => {
    if (open && !wasOpen.current) {
      setStep('choose')
      setDeckId(null)
      setAsCommander(false)
      setCreatedId(null)
    }

    wasOpen.current = open
  }, [open])

  async function bind(targetId: string, commander: boolean) {
    if (!copy) {
      return
    }

    if (mode === 'move' && fromDeckId) {
      await moveDeckCard(fromDeckId, copy.id, targetId, commander)
      return
    }

    if (mode === 'take') {
      await takeCopy(targetId, copy.id, commander)
      return
    }

    await requestCopy(targetId, copy.id, groupId)
  }

  async function run(action: () => Promise<unknown>) {
    setSaving(true)

    try {
      await action()
      await onDone()
    } catch (error) {
      toastError(error)
      await invalidateBoard(queryClient)
    } finally {
      setSaving(false)
    }
  }

  const title =
    step === 'create'
      ? 'Criar deck'
      : mode === 'request'
        ? 'Solicitar para o deck'
        : 'Selecionar deck'
  const cardName = copy
    ? (copy.catalog.name_pt ?? copy.catalog.name_en)
    : undefined

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title={title}
      description={cardName}
    >
      {step === 'choose' ? (
        <div className="flex flex-col gap-2">
          <ChoiceButton
            title="Criar um deck novo"
            detail="Dá um nome e escolhe o formato."
            onClick={() => {
              setStep('create')
            }}
          />
          <ChoiceButton
            title={
              mode === 'request'
                ? 'Solicitar para um deck que já existe'
                : mode === 'move'
                  ? 'Mover para um deck que já existe'
                  : 'Adicionar a um deck que já existe'
            }
            detail={
              decks.length === 0
                ? 'Você ainda não tem nenhum deck.'
                : allowCommander
                  ? 'Escolhe o deck e, se quiser, marca a carta como comandante.'
                  : 'Escolhe o deck de destino.'
            }
            disabled={decks.length === 0}
            onClick={() => {
              setStep('existing')

              if (
                preferredDeckId &&
                decks.some((deck) => deck.id === preferredDeckId)
              ) {
                setDeckId(preferredDeckId)
                setAsCommander(false)
              }
            }}
          />
        </div>
      ) : null}
      {step === 'create' ? (
        <CreateStep
          createdId={createdId}
          saving={saving}
          submitLabel={createLabel(mode, createdId != null)}
          onBack={() => {
            setStep('choose')
          }}
          onSubmit={(values) =>
            run(async () => {
              const targetId = createdId ?? (await createDeck(values)).id
              setCreatedId(targetId)
              await bind(targetId, false)
            })
          }
        />
      ) : null}
      {step === 'existing' ? (
        <div className="flex flex-col gap-4">
          <Button
            type="button"
            variant="ghost"
            className="self-start"
            disabled={saving}
            onClick={() => {
              setStep('choose')
            }}
          >
            Voltar
          </Button>
          {decks.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Você ainda não tem nenhum deck.
            </p>
          ) : (
            <fieldset className="flex flex-col gap-2">
              <legend className="sr-only">Deck</legend>
              {decks.map((deck) => {
                const checked = deck.id === deckId

                return (
                  <label
                    key={deck.id}
                    className={cn(
                      'flex gap-2 rounded-lg p-3 ring-1 ring-foreground/10',
                      checked && 'bg-muted',
                    )}
                  >
                    <input
                      type="radio"
                      name="destination-deck"
                      value={deck.id}
                      checked={checked}
                      onChange={() => {
                        setDeckId(deck.id)
                        setAsCommander(false)
                      }}
                    />
                    <span>
                      <span className="font-medium">{deck.name}</span>
                      <FieldDescription>
                        {deckFormatLabel(deck.format)}
                        {' · '}
                        {seated(deck)}
                      </FieldDescription>
                    </span>
                  </label>
                )
              })}
            </fieldset>
          )}
          {allowCommander && selected && cardFacts ? (
            checkingColors ? (
              <div
                className="flex flex-col gap-2"
                aria-busy="true"
                aria-label="Conferindo comandantes"
              >
                <Skeleton className="h-5 w-56" />
                <Skeleton className="h-4 w-full" />
              </div>
            ) : (
              <label className="flex gap-2 text-sm">
                <input
                  type="checkbox"
                  className="mt-0.5"
                  checked={asCommander && commanderAllowed}
                  disabled={!commanderAllowed || saving}
                  onChange={(event) => {
                    setAsCommander(event.target.checked)
                  }}
                />
                <span>
                  Adicionar como comandante
                  <FieldDescription>
                    {commanderReason ??
                      seatHint(selected, commanderFacts.length)}
                  </FieldDescription>
                </span>
              </label>
            )
          ) : null}
          {mode === 'move' ? (
            <p className="text-sm text-muted-foreground">
              No deck de origem ela deixa de ser comandante, se era.
            </p>
          ) : null}
          <Button
            type="button"
            disabled={saving || deckId == null || checkingColors}
            onClick={() => {
              if (!deckId) {
                return
              }

              void run(() =>
                bind(deckId, allowCommander && asCommander && commanderAllowed),
              )
            }}
          >
            {saving ? <Loader2Icon className="animate-spin" /> : null}
            {existingLabel(mode)}
          </Button>
        </div>
      ) : null}
    </Dialog>
  )
}

function ChoiceButton({
  title,
  detail,
  disabled = false,
  onClick,
}: {
  title: string
  detail: string
  disabled?: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      className="flex flex-col gap-1 rounded-lg p-3 text-left ring-1 ring-foreground/10 hover:bg-muted disabled:pointer-events-none disabled:opacity-50"
      onClick={onClick}
    >
      <span className="font-medium">{title}</span>
      <span className="text-sm text-muted-foreground">{detail}</span>
    </button>
  )
}

function CreateStep({
  createdId,
  saving,
  submitLabel,
  onBack,
  onSubmit,
}: {
  createdId: string | null
  saving: boolean
  submitLabel: string
  onBack: () => void
  onSubmit: (values: CreateDeckInput) => Promise<void>
}) {
  const form = useForm<CreateDeckInput>({
    resolver: zodResolver(createDeckInputSchema),
    defaultValues: {
      name: '',
      format: 'commander_10',
    },
  })

  return (
    <form
      className="flex flex-col gap-4"
      noValidate
      onSubmit={form.handleSubmit((values) => onSubmit(values))}
    >
      <Button
        type="button"
        variant="ghost"
        className="self-start"
        disabled={saving}
        onClick={onBack}
      >
        Voltar
      </Button>
      {createdId ? (
        <p className="text-sm text-muted-foreground">
          O deck já foi criado. Esta tentativa só coloca a carta.
        </p>
      ) : null}
      <FieldGroup>
        <Controller
          name="name"
          control={form.control}
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <FieldLabel htmlFor="select-deck-name">Nome</FieldLabel>
              <Input
                {...field}
                id="select-deck-name"
                aria-invalid={fieldState.invalid}
                disabled={createdId != null || saving}
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
                  <label
                    key={format.value}
                    className="flex gap-2 rounded-lg p-3 ring-1 ring-foreground/10"
                  >
                    <input
                      type="radio"
                      name={field.name}
                      value={format.value}
                      checked={field.value === format.value}
                      disabled={createdId != null || saving}
                      onChange={() => {
                        field.onChange(format.value)
                      }}
                    />
                    <span>
                      <span className="font-medium">{format.label}</span>
                      <FieldDescription>{format.hint}</FieldDescription>
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
      <Button type="submit" disabled={saving}>
        {saving ? <Loader2Icon className="animate-spin" /> : null}
        {submitLabel}
      </Button>
    </form>
  )
}

function factsFromCopy(copy: Copy): CommanderFacts {
  return {
    nameEn: copy.catalog.name_en,
    canBeCommander: copy.catalog.can_be_commander,
    partnerKind: copy.catalog.partner_kind,
    oracleText: copy.catalog.oracle_text,
    typeLine: copy.catalog.type_line ?? '',
    keywords: copy.catalog.keywords,
  }
}

function factsFromCommander(
  card: DeckSummary['commanders'][number],
): CommanderFacts {
  return {
    nameEn: card.name_en,
    canBeCommander: card.can_be_commander,
    partnerKind: card.partner_kind,
    oracleText: card.oracle_text,
    typeLine: card.type_line,
    keywords: card.keywords,
  }
}

function seated(deck: DeckSummary) {
  if (deck.commanders.length === 0) {
    return 'Sem comandante'
  }

  const names = deck.commanders.map((card) => card.name_pt ?? card.name_en)

  return deck.commanders.length === 1
    ? `Comandante: ${names[0]}`
    : `Comandantes: ${names.join(' e ')}`
}

function seatHint(deck: DeckSummary, count: number) {
  if (count === 0) {
    return 'O deck ainda não tem comandante.'
  }

  const name = deck.commanders[0]?.name_pt ?? deck.commanders[0]?.name_en

  return name
    ? `${name} aceita esta carta como segundo comandante.`
    : 'Esta carta pode ser o segundo comandante.'
}

function createLabel(mode: DeckMode, alreadyCreated: boolean) {
  if (alreadyCreated) {
    return existingLabel(mode)
  }

  if (mode === 'request') {
    return 'Criar e solicitar'
  }

  if (mode === 'move') {
    return 'Criar e mover'
  }

  return 'Criar e adicionar'
}

function existingLabel(mode: DeckMode) {
  if (mode === 'request') {
    return 'Solicitar'
  }

  if (mode === 'move') {
    return 'Mover'
  }

  return 'Adicionar'
}
