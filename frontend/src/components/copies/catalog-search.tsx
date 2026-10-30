import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { CardThumb } from '@/components/cards/card-thumb'
import { CardTitle } from '@/components/cards/card-title'
import { ManaCost } from '@/components/cards/mana-cost'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { catalogQueryOptions } from '@/lib/api/catalog'
import type { CatalogCard } from '@/lib/api/catalog'
import { apiErrorMessage } from '@/lib/api/client'
import { formatColorIdentity } from '@/lib/display'

export function CatalogSearch({
  onSelect,
  deckId,
}: {
  onSelect: (card: CatalogCard) => void
  deckId?: string
}) {
  const [text, setText] = useState('')
  const [q, setQ] = useState('')

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      setQ(text.trim())
    }, 150)

    return () => {
      window.clearTimeout(timeout)
    }
  }, [text])

  const query = useQuery({
    ...catalogQueryOptions(q, deckId),
    enabled: q.length >= 2,
  })

  return (
    <div className="flex flex-col gap-3">
      <Input
        value={text}
        onChange={(event) => {
          setText(event.target.value)
        }}
        placeholder="Nome em português ou inglês"
        aria-label="Buscar carta"
        autoComplete="off"
      />
      {text.trim().length > 0 && q.length < 2 ? (
        <p className="text-sm text-muted-foreground">
          Digite pelo menos 2 caracteres.
        </p>
      ) : null}
      {query.isFetching ? (
        <p className="text-sm text-muted-foreground">Buscando…</p>
      ) : null}
      {query.isError ? (
        <p role="alert" className="text-sm text-destructive">
          {apiErrorMessage(query.error)}
        </p>
      ) : null}
      {query.data && query.data.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Nenhuma carta encontrada.
        </p>
      ) : null}
      {query.data && query.data.length > 0 ? (
        <ul className="flex max-h-64 flex-col gap-2 overflow-auto">
          {query.data.map((card) => (
            <li key={card.oracle_id}>
              <button
                type="button"
                className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left hover:bg-muted"
                onClick={() => {
                  onSelect(card)
                }}
              >
                <CardThumb url={card.image_url} />
                <div className="flex min-w-0 flex-col gap-1">
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                    <CardTitle namePt={card.name_pt} nameEn={card.name_en} />
                    <ManaCost cost={card.mana_cost} />
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {[card.type_line, formatColorIdentity(card.color_identity)]
                      .filter(Boolean)
                      .join(' · ')}
                  </p>
                  {card.is_basic ? (
                    <Badge variant="secondary">Básica</Badge>
                  ) : null}
                </div>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
