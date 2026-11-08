import { useState } from 'react'
import { useQueryClient, useSuspenseQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { LayoutGridIcon, ListIcon, Trash2Icon } from 'lucide-react'

import { CardThumb } from '@/components/cards/card-thumb'
import { ColorIdentity } from '@/components/cards/color-identity'
import { ConfirmDialog } from '@/components/confirm-dialog'
import { CreateDeckDialog } from '@/components/decks/create-deck-dialog'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { deleteDeck, decksQueryOptions } from '@/lib/api/decks'
import type { DeckSummary } from '@/lib/api/decks'
import { invalidateBoard, reportBoardError } from '@/lib/api/invalidate'
import { deckFormatLabel } from '@/lib/display'
import { cn } from '@/lib/utils'

type DeckView = 'grade' | 'lista'

const VIEW_PREFERENCE_KEY = 'magic-bulk.decks-view'

function useDeckView() {
  const [view, setView] = useState<DeckView>(() => {
    if (typeof localStorage === 'undefined') {
      return 'grade'
    }

    return localStorage.getItem(VIEW_PREFERENCE_KEY) === 'lista'
      ? 'lista'
      : 'grade'
  })

  function changeView(next: DeckView) {
    setView(next)

    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(VIEW_PREFERENCE_KEY, next)
    }
  }

  return [view, changeView] as const
}

function commanderNames(commanders: DeckSummary['commanders']) {
  if (commanders.length === 0) {
    return 'Sem comandante'
  }

  return commanders.map((card) => card.name_pt ?? card.name_en).join(' + ')
}

function cardCountText(count: number) {
  return `${count} ${count === 1 ? 'carta' : 'cartas'}`
}

function DeckCovers({
  commanders,
  view,
}: {
  commanders: DeckSummary['commanders']
  view: DeckView
}) {
  const shown = commanders.slice(0, 2)

  if (view === 'lista') {
    return (
      <div className="flex shrink-0 gap-1">
        {shown.length === 0 ? (
          <div
            className="flex h-16 w-11 items-center justify-center rounded bg-muted text-xs text-muted-foreground"
            title="Sem comandante"
            aria-label="Sem comandante"
          >
            —
          </div>
        ) : (
          shown.map((card) => (
            <CardThumb
              key={card.name_en}
              url={card.image_url}
              className="h-16 w-11"
            />
          ))
        )}
      </div>
    )
  }

  if (shown.length === 0) {
    return (
      <div className="flex aspect-[488/680] items-center justify-center bg-muted/60 p-4 text-center text-sm text-muted-foreground">
        Sem comandante
      </div>
    )
  }

  return (
    <div
      className={cn(
        'grid bg-muted',
        shown.length > 1 ? 'grid-cols-2' : 'grid-cols-1',
      )}
    >
      {shown.map((card) => (
        <CardThumb
          key={card.name_en}
          url={card.image_url}
          preview={false}
          className="aspect-[488/680] h-auto w-full rounded-none object-cover"
        />
      ))}
    </div>
  )
}

function DeckViewToggle({
  view,
  onChange,
}: {
  view: DeckView
  onChange: (view: DeckView) => void
}) {
  const options = [
    { id: 'grade' as const, label: 'Grade', icon: LayoutGridIcon },
    { id: 'lista' as const, label: 'Lista', icon: ListIcon },
  ]

  return (
    <div role="group" aria-label="Organização" className="flex shrink-0">
      {options.map((option) => {
        const Icon = option.icon
        const selected = view === option.id

        return (
          <Button
            key={option.id}
            type="button"
            variant="outline"
            aria-pressed={selected}
            className={cn(
              option.id === 'grade'
                ? 'rounded-r-none'
                : '-ml-px rounded-l-none',
              selected && 'bg-muted',
            )}
            onClick={() => {
              onChange(option.id)
            }}
          >
            <Icon />
            {option.label}
          </Button>
        )
      })}
    </div>
  )
}

export function DecksPage({ groupId }: { groupId: string }) {
  const queryClient = useQueryClient()
  const { data: decks } = useSuspenseQuery(decksQueryOptions())
  const [view, changeView] = useDeckView()
  const [createOpen, setCreateOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<DeckSummary | null>(null)
  const [deleting, setDeleting] = useState(false)

  async function removeDeck() {
    if (!deleteTarget) {
      return
    }

    setDeleting(true)

    try {
      await deleteDeck(deleteTarget.id)
      await invalidateBoard(queryClient)
    } catch (error) {
      await reportBoardError(queryClient, error)
    } finally {
      setDeleting(false)
      setDeleteTarget(null)
    }
  }

  function deckDeleteButton(deck: DeckSummary) {
    return (
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        aria-label={`Apagar deck ${deck.name}`}
        title="Apagar deck"
        className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
        onClick={() => {
          setDeleteTarget(deck)
        }}
      >
        <Trash2Icon />
      </Button>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Decks"
        action={
          <div className="flex flex-wrap items-center gap-2">
            <DeckViewToggle view={view} onChange={changeView} />
            <Button
              type="button"
              onClick={() => {
                setCreateOpen(true)
              }}
            >
              Criar deck
            </Button>
          </div>
        }
      />
      {decks.length === 0 ? (
        <div className="flex flex-col items-start gap-3">
          <p>Você ainda não tem nenhum deck.</p>
          <Button
            type="button"
            onClick={() => {
              setCreateOpen(true)
            }}
          >
            Criar deck
          </Button>
        </div>
      ) : view === 'lista' ? (
        <ul className="flex flex-col gap-3">
          {decks.map((deck) => (
            <li
              key={deck.id}
              className="relative rounded-xl bg-card ring-1 ring-foreground/10 focus-within:ring-2 focus-within:ring-ring"
            >
              <Link
                to="/grupos/$groupId/decks/$deckId"
                params={{ groupId, deckId: deck.id }}
                className="flex flex-wrap items-center gap-4 p-4 pr-14 outline-none"
              >
                <DeckCovers commanders={deck.commanders} view="lista" />
                <div className="flex min-w-0 flex-1 basis-52 flex-col gap-1">
                  <p className="font-heading text-lg font-medium">
                    {deck.name}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {deckFormatLabel(deck.format)}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {commanderNames(deck.commanders)}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm sm:flex-col sm:items-end">
                  <ColorIdentity
                    colors={deck.color_identity}
                    name={deck.color_identity_name}
                  />
                  <span className="text-muted-foreground">
                    {cardCountText(deck.card_count)}
                  </span>
                </div>
              </Link>
              <div className="absolute bottom-3 right-3 z-10">
                {deckDeleteButton(deck)}
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
          {decks.map((deck) => (
            <li
              key={deck.id}
              className="relative flex flex-col overflow-hidden rounded-xl bg-card ring-1 ring-foreground/10 focus-within:ring-2 focus-within:ring-ring"
            >
              <Link
                to="/grupos/$groupId/decks/$deckId"
                params={{ groupId, deckId: deck.id }}
                className="flex flex-1 flex-col outline-none"
              >
                <DeckCovers commanders={deck.commanders} view="grade" />
                <div className="flex flex-1 flex-col gap-2 p-4">
                  <div className="flex flex-col gap-1">
                    <p className="font-heading text-lg font-medium leading-snug">
                      {deck.name}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {deckFormatLabel(deck.format)}
                    </p>
                  </div>
                  <div className="mt-auto flex flex-col gap-1 text-sm">
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                      <ColorIdentity
                        colors={deck.color_identity}
                        name={deck.color_identity_name}
                      />
                      <span className="text-muted-foreground">
                        {cardCountText(deck.card_count)}
                      </span>
                    </div>
                    <p className="text-muted-foreground">
                      {commanderNames(deck.commanders)}
                    </p>
                  </div>
                </div>
              </Link>
              <div className="flex justify-end border-t border-border/60 px-2 py-1">
                {deckDeleteButton(deck)}
              </div>
            </li>
          ))}
        </ul>
      )}
      <CreateDeckDialog open={createOpen} onOpenChange={setCreateOpen} />
      <ConfirmDialog
        open={deleteTarget != null}
        onOpenChange={(open) => {
          if (!open) {
            setDeleteTarget(null)
          }
        }}
        title="Apagar deck"
        description="As cartas voltam para o bulk, livres, na casa de quem está com elas, inclusive as travadas."
        confirmLabel="Apagar"
        destructive
        pending={deleting}
        onConfirm={() => {
          void removeDeck()
        }}
      />
    </div>
  )
}
