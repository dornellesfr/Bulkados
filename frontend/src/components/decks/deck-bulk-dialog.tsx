import { useEffect, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { AlertCircleIcon, Loader2Icon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { apiErrorMessage } from '@/lib/api/client'
import { replaceDeckCards, validateDeckCards } from '@/lib/api/decks'
import type { DeckBulkCard, DeckDetail } from '@/lib/api/decks'
import { invalidateBoard } from '@/lib/api/invalidate'
import { buildBulkText, parseBulkText } from '@/lib/deck-view'
import { cn } from '@/lib/utils'

class UnknownBulkCardsError extends Error {
  readonly names: Array<string>

  constructor(names: Array<string>) {
    super('Não reconhecemos algumas cartas.')
    this.name = 'UnknownBulkCardsError'
    this.names = names
  }
}

function linesWithUnknown(text: string, unknown: Array<string>) {
  const names = new Set(unknown)
  const lines = new Set<number>()

  text.split('\n').forEach((line, index) => {
    if (parseBulkText(line).some((card) => names.has(card.name))) {
      lines.add(index)
    }
  })

  return lines
}

export function DeckBulkDialog({
  deck,
  open,
  onOpenChange,
}: {
  deck: DeckDetail
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const queryClient = useQueryClient()
  const [text, setText] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [unknownLines, setUnknownLines] = useState<Set<number>>(new Set())
  const highlightRef = useRef<HTMLDivElement>(null)
  const mutation = useMutation({
    mutationFn: async (input: { cards: Array<DeckBulkCard>; text: string }) => {
      const validation = await validateDeckCards(deck.id, {
        cards: input.cards,
      })
      if (validation.unknown.length > 0) {
        throw new UnknownBulkCardsError(validation.unknown)
      }
      return replaceDeckCards(deck.id, { cards: input.cards })
    },
    onSuccess: async () => {
      await invalidateBoard(queryClient)
      onOpenChange(false)
    },
    onError: (cause, variables) => {
      if (cause instanceof UnknownBulkCardsError) {
        setUnknownLines(linesWithUnknown(variables.text, cause.names))
        setError(null)
        return
      }

      setUnknownLines(new Set())
      setError(apiErrorMessage(cause))
    },
  })

  useEffect(() => {
    if (open) {
      setText(buildBulkText(deck))
      setError(null)
      setUnknownLines(new Set())
    }
  }, [deck, open])

  const lines = text.split('\n')

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!mutation.isPending) {
          onOpenChange(next)
        }
      }}
      title="Editar em bulk"
      description="Uma linha por carta. Os nomes são conferidos antes de salvar; se algum não for reconhecido, nada é alterado. Use # Comandante para a seção do comandante."
      wide
    >
      <form
        className="flex flex-col gap-4"
        noValidate
        aria-busy={mutation.isPending}
        onSubmit={(event) => {
          event.preventDefault()
          setError(null)
          setUnknownLines(new Set())
          mutation.mutate({ cards: parseBulkText(text), text })
        }}
      >
        {unknownLines.size > 0 ? (
          <p
            role="alert"
            className="flex items-start gap-2 rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive"
          >
            <AlertCircleIcon className="mt-0.5 size-4 shrink-0" />
            <span>
              {unknownLines.size === 1
                ? '1 linha não foi reconhecida. Ela está sublinhada.'
                : `${unknownLines.size} linhas não foram reconhecidas. Elas estão sublinhadas.`}
            </span>
          </p>
        ) : null}
        {error ? (
          <p
            role="alert"
            className="flex items-start gap-2 rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive"
          >
            <AlertCircleIcon className="mt-0.5 size-4 shrink-0" />
            <span>{error}</span>
          </p>
        ) : null}
        <div className="relative">
          <Textarea
            value={text}
            onChange={(event) => {
              setText(event.target.value)
            }}
            onScroll={(event) => {
              const highlight = highlightRef.current

              if (highlight) {
                highlight.scrollTop = event.currentTarget.scrollTop
                highlight.scrollLeft = event.currentTarget.scrollLeft
              }
            }}
            disabled={mutation.isPending}
            aria-invalid={unknownLines.size > 0 || error != null}
            spellCheck={false}
            autoComplete="off"
            aria-label="Lista de cartas do deck"
            placeholder={
              '# Comandante\n1x Nome do comandante\n\n# Criaturas\n1x Nome da carta'
            }
            className="min-h-[52vh] resize-y font-mono text-sm leading-6"
          />
          <div
            ref={highlightRef}
            aria-hidden
            className="pointer-events-none absolute inset-0 z-10 overflow-hidden rounded-lg border border-transparent px-2.5 py-2 font-mono text-sm leading-6 break-words whitespace-pre-wrap text-transparent [scrollbar-gutter:stable]"
          >
            {lines.map((line, index) => (
              <span
                key={index}
                className={cn(
                  unknownLines.has(index)
                    ? 'underline decoration-destructive decoration-2 underline-offset-4'
                    : null,
                )}
              >
                {line}
                {index < lines.length - 1 ? '\n' : null}
              </span>
            ))}
          </div>
        </div>
        <p className="text-xs text-muted-foreground">
          Aceita “1x Nome”, “1 Nome” ou só o nome. Informações de edição como
          (NEO) 132 são ignoradas. Linhas em branco e títulos de seção não
          contam como cartas.
        </p>
        <div className="flex justify-end gap-2">
          <Button
            type="button"
            variant="outline"
            disabled={mutation.isPending}
            onClick={() => {
              onOpenChange(false)
            }}
          >
            Cancelar
          </Button>
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? (
              <Loader2Icon className="animate-spin" />
            ) : null}
            {mutation.isPending ? 'Verificando cartas…' : 'Salvar lista'}
          </Button>
        </div>
      </form>
    </Dialog>
  )
}
