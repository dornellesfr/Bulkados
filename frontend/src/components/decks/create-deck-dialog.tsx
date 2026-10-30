import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
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
import { createDeck, createDeckInputSchema } from '@/lib/api/decks'
import type { CreateDeckInput, DeckSummary } from '@/lib/api/decks'
import { invalidateBoard, toastError } from '@/lib/api/invalidate'
import { deckFormats } from '@/lib/display'

export function CreateDeckDialog({
  open,
  onOpenChange,
  groupId,
  onCreated,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  groupId: string
  onCreated?: (deck: DeckSummary) => void
}) {
  const queryClient = useQueryClient()
  const form = useForm<CreateDeckInput>({
    resolver: zodResolver(createDeckInputSchema),
    defaultValues: {
      name: '',
      format: 'commander_10',
    },
  })
  const mutation = useMutation({
    mutationFn: (values: CreateDeckInput) => createDeck(groupId, values),
    onSuccess: async (deck) => {
      await invalidateBoard(queryClient)
      form.reset({ name: '', format: 'commander_10' })
      onOpenChange(false)
      onCreated?.(deck)
    },
    onError: (error) => {
      toastError(error)
    },
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange} title="Criar deck">
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
                <FieldLabel htmlFor="deck-name">Nome</FieldLabel>
                <Input
                  {...field}
                  id="deck-name"
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
                    <label
                      key={format.value}
                      className="flex gap-2 rounded-lg p-3 ring-1 ring-foreground/10"
                    >
                      <input
                        type="radio"
                        name={field.name}
                        value={format.value}
                        checked={field.value === format.value}
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
        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? <Loader2Icon className="animate-spin" /> : null}
          Criar
        </Button>
      </form>
    </Dialog>
  )
}
