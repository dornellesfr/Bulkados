import { useEffect, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { AlertCircleIcon, Loader2Icon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { apiErrorMessage } from '@/lib/api/client'
import { replaceDeckCards } from '@/lib/api/decks'
import type { DeckBulkInput, DeckDetail } from '@/lib/api/decks'
import { invalidateBoard } from '@/lib/api/invalidate'
import { buildBulkText, parseBulkText } from '@/lib/deck-view'

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
  const mutation = useMutation({
    mutationFn: (input: DeckBulkInput) => replaceDeckCards(deck.id, input),
    onSuccess: async () => {
      await invalidateBoard(queryClient)
      onOpenChange(false)
    },
    onError: (cause) => {
      setError(apiErrorMessage(cause))
    },
  })

  useEffect(() => {
    if (open) {
      setText(buildBulkText(deck))
      setError(null)
    }
  }, [deck, open])

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!mutation.isPending) {
          onOpenChange(next)
        }
      }}
      title="Editar em bulk"
      description="Uma linha por carta, no formato 1x Nome. Use # Comandante para a seção do comandante. Se qualquer nome não for reconhecido, nada é alterado."
      wide
    >
      <form
        className="flex flex-col gap-4"
        noValidate
        onSubmit={(event) => {
          event.preventDefault()
          setError(null)
          mutation.mutate({ cards: parseBulkText(text) })
        }}
      >
        <Textarea
          value={text}
          onChange={(event) => {
            setText(event.target.value)
            setError(null)
          }}
          spellCheck={false}
          autoComplete="off"
          aria-label="Lista de cartas do deck"
          placeholder={
            '# Comandante\n1x Nome do comandante\n\n# Criaturas\n1x Nome da carta'
          }
          className="min-h-[52vh] resize-y font-mono text-sm leading-6"
        />
        <p className="text-xs text-muted-foreground">
          Linhas em branco e títulos de seção não contam como cartas. Aceita
          também listas com quantidade, como 2x Nome.
        </p>
        {error ? (
          <p
            role="alert"
            className="flex items-start gap-2 rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive"
          >
            <AlertCircleIcon className="mt-0.5 size-4 shrink-0" />
            <span>{error}</span>
          </p>
        ) : null}
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
            Salvar lista
          </Button>
        </div>
      </form>
    </Dialog>
  )
}
