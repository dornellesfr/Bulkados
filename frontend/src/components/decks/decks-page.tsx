import { useState } from 'react'
import { useSuspenseQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'

import { CreateDeckDialog } from '@/components/decks/create-deck-dialog'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { decksQueryOptions } from '@/lib/api/decks'
import { deckFormatLabel } from '@/lib/display'

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
                className="block rounded-xl bg-card p-4 ring-1 ring-foreground/10"
              >
                <p className="font-medium">{deck.name}</p>
                <p className="text-sm text-muted-foreground">
                  {deckFormatLabel(deck.format)}
                </p>
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
