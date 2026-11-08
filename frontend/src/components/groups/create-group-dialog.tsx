import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { Loader2Icon } from 'lucide-react'
import { Controller, useForm } from 'react-hook-form'

import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { createGroup, groupNameInputSchema } from '@/lib/api/groups'
import type { GroupNameInput } from '@/lib/api/groups'
import { invalidateMembership } from '@/lib/api/invalidate'
import { applyApiFormError } from '@/lib/form-error'

export function CreateGroupDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const form = useForm<GroupNameInput>({
    resolver: zodResolver(groupNameInputSchema),
    defaultValues: { name: '' },
  })
  const mutation = useMutation({
    mutationFn: createGroup,
    onSuccess: async (group) => {
      await invalidateMembership(queryClient)
      onOpenChange(false)
      form.reset()
      await navigate({
        to: '/grupos/$groupId',
        params: { groupId: group.id },
      })
    },
    onError: (error) => {
      applyApiFormError(form.setError, error, {})
    },
  })

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!mutation.isPending) {
          onOpenChange(next)
          if (!next) {
            form.reset()
          }
        }
      }}
      title="Criar grupo"
    >
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
                <FieldLabel htmlFor="group-name">Nome</FieldLabel>
                <Input
                  {...field}
                  id="group-name"
                  aria-invalid={fieldState.invalid}
                  autoFocus
                />
                {fieldState.invalid ? (
                  <FieldError errors={[fieldState.error]} />
                ) : null}
              </Field>
            )}
          />
        </FieldGroup>
        {form.formState.errors.root ? (
          <p role="alert" className="text-sm text-destructive">
            {form.formState.errors.root.message}
          </p>
        ) : null}
        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? <Loader2Icon className="animate-spin" /> : null}
          Criar
        </Button>
      </form>
    </Dialog>
  )
}
