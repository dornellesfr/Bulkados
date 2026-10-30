import { useState } from 'react'
import { useSuspenseQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'

import { CardThumb } from '@/components/cards/card-thumb'
import { ColorIdentity } from '@/components/cards/color-identity'
import { CreateDeckDialog } from '@/components/decks/create-deck-dialog'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { decksQueryOptions } from '@/lib/api/decks'
import type { DeckSummary } from '@/lib/api/decks'
import { deckFormatLabel } from '@/lib/display'

function commandersText(commanders: DeckSummary['commanders']) {
  if (commanders.length === 0) {
    return 'Sem comandante'
  }

  const names = commanders
    .map((card) =>
      card.name_pt ? `${card.name_pt} (${card.name_en})` : card.name_en,
    )
    .join(' + ')

  return `${commanders.length === 1 ? 'Comandante' : 'Comandantes'}: ${names}`
}

export function DecksPage({ groupId }: { groupId: string }) {
  const { data: decks } = useSuspenseQuery(decksQueryOptions(groupId))
  const [createOpen, setCreateOpen] = useState(false)

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Decks"
        action={
          <Button
            type="button"
            onClick={() => {
              setCreateOpen(true)
            }}
          >
            Criar deck
          </Button>
        }
      />
      {decks.length === 0 ? (
        <div className="flex flex-col items-start gap-3">
          <p>Você ainda não tem um deck neste grupo.</p>
          <Button
            type="button"
            onClick={() => {
              setCreateOpen(true)
            }}
          >
            Criar deck
          </Button>
        </div>
      ) : (
        <ul className="flex flex-col gap-3">
          {decks.map((deck) => (
            <li key={deck.id}>
              <Link
                to="/grupos/$groupId/decks/$deckId"
                params={{ groupId, deckId: deck.id }}
                className="flex items-center gap-4 rounded-xl bg-card p-4 ring-1 ring-foreground/10"
              >
                <div className="flex shrink-0 gap-1">
                  {deck.commanders.length === 0 ? (
                    <CardThumb url={null} />
                  ) : (
                    deck.commanders.map((card) => (
                      <CardThumb key={card.name_en} url={card.image_url} />
                    ))
                  )}
                </div>
                <div className="flex min-w-0 flex-col gap-1">
                  <p className="font-medium">{deck.name}</p>
                  <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
                    <span>{deckFormatLabel(deck.format)}</span>
                    <ColorIdentity
                      colors={deck.color_identity}
                      name={deck.color_identity_name}
                    />
                  </p>
                  <p className="text-sm">{commandersText(deck.commanders)}</p>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
      <CreateDeckDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        groupId={groupId}
      />
    </div>
  )
}
