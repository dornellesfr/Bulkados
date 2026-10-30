import { useEffect, useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import {
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { Loader2Icon } from 'lucide-react'
import { Controller, useForm } from 'react-hook-form'
import { z } from 'zod'

import { CatalogSearch } from '@/components/copies/catalog-search'
import { CardTitle } from '@/components/cards/card-title'
import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { NativeSelect } from '@/components/ui/native-select'
import type { CatalogCard } from '@/lib/api/catalog'
import { createCopies } from '@/lib/api/copies'
import { groupsQueryOptions, membersQueryOptions } from '@/lib/api/groups'
import type { Member } from '@/lib/api/groups'
import { invalidateBoard, toastError } from '@/lib/api/invalidate'
import { quantitySchema } from '@/lib/api/schemas'

const formSchema = z.object({
  quantity: quantitySchema,
  holderId: z.string().min(1, 'Escolha a casa.'),
  linkAll: z.boolean(),
  groupIds: z.array(z.string()),
})

type FormValues = z.infer<typeof formSchema>

function acceptedIntersection(lists: Array<Array<Member>>) {
  if (lists.length === 0) {
    return []
  }

  const [first, ...rest] = lists

  return first.filter(
    (member) =>
      member.status === 'accepted' &&
      rest.every((list) =>
        list.some(
          (item) =>
            item.user_id === member.user_id && item.status === 'accepted',
        ),
      ),
  )
}

export function RegisterCopyDialog({
  open,
  onOpenChange,
  groupId,
  meId,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  groupId: string
  meId: string
}) {
  const queryClient = useQueryClient()
  const [card, setCard] = useState<CatalogCard | null>(null)
  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      quantity: 1,
      holderId: meId,
      linkAll: true,
      groupIds: [],
    },
  })
  const holderId = form.watch('holderId')
  const linkAll = form.watch('linkAll')
  const groupIds = form.watch('groupIds')
  const groups = useQuery({
    ...groupsQueryOptions(),
    enabled: open,
  })
  const explicitGroupIds =
    holderId === meId && linkAll ? [groupId] : [groupId, ...groupIds]
  const memberQueries = useQueries({
    queries: explicitGroupIds.map((id) => ({
      ...membersQueryOptions(id),
      enabled: open,
    })),
  })
  const membersReady = memberQueries.every((query) => query.isSuccess)
  const holders = membersReady
    ? acceptedIntersection(memberQueries.map((query) => query.data))
    : []

  useEffect(() => {
    if (!open || !membersReady) {
      return
    }

    if (holders.some((member) => member.user_id === holderId)) {
      return
    }

    form.setValue('holderId', meId)
    form.setValue('linkAll', groupIds.length === 0)
  }, [form, groupIds.length, holderId, holders, meId, membersReady, open])

  const mutation = useMutation({
    mutationFn: () => {
      const values = form.getValues()
      return createCopies(groupId, {
        oracle_id: card?.oracle_id ?? '',
        quantity: values.quantity,
        ...(values.holderId !== meId ? { holder_id: values.holderId } : {}),
        ...(values.holderId === meId && values.linkAll
          ? {}
          : values.groupIds.length > 0
            ? { group_ids: values.groupIds }
            : {}),
      })
    },
    onSuccess: async () => {
      await invalidateBoard(queryClient)
      setCard(null)
      form.reset({
        quantity: 1,
        holderId: meId,
        linkAll: true,
        groupIds: [],
      })
      onOpenChange(false)
    },
    onError: (error) => {
      toastError(error)
    },
  })

  const otherGroups = (groups.data ?? []).filter(
    (group) => group.id !== groupId,
  )
  const showLinkAll = holderId === meId

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (mutation.isPending) {
          return
        }

        if (!next) {
          setCard(null)
          form.reset({
            quantity: 1,
            holderId: meId,
            linkAll: true,
            groupIds: [],
          })
        }

        onOpenChange(next)
      }}
      title="Cadastrar carta"
      description="A casa padrão é você. O grupo desta página sempre entra."
    >
      {card ? (
        <form
          className="flex flex-col gap-4"
          noValidate
          onSubmit={form.handleSubmit(() => mutation.mutateAsync())}
        >
          <div className="flex items-start justify-between gap-3">
            <CardTitle namePt={card.name_pt} nameEn={card.name_en} />
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setCard(null)
              }}
            >
              Trocar
            </Button>
          </div>
          <FieldGroup>
            <Controller
              name="quantity"
              control={form.control}
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor="copy-quantity">Quantidade</FieldLabel>
                  <Input
                    id="copy-quantity"
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
            <Controller
              name="holderId"
              control={form.control}
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor="copy-holder">Casa</FieldLabel>
                  <NativeSelect
                    id="copy-holder"
                    value={field.value}
                    onChange={(event) => {
                      const next = event.target.value
                      field.onChange(next)

                      if (next === meId) {
                        form.setValue('linkAll', true)
                        form.setValue('groupIds', [])
                      } else {
                        form.setValue('linkAll', false)
                      }
                    }}
                    disabled={!membersReady}
                    aria-invalid={fieldState.invalid}
                  >
                    {holders.map((member) => (
                      <option key={member.user_id} value={member.user_id}>
                        {member.nick}
                      </option>
                    ))}
                  </NativeSelect>
                  {fieldState.invalid ? (
                    <FieldError errors={[fieldState.error]} />
                  ) : null}
                </Field>
              )}
            />
          </FieldGroup>
          {showLinkAll ? (
            <Controller
              name="linkAll"
              control={form.control}
              render={({ field }) => (
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={field.value}
                    onChange={(event) => {
                      field.onChange(event.target.checked)
                      if (event.target.checked) {
                        form.setValue('groupIds', [])
                      }
                    }}
                  />
                  Vincular a todos os meus grupos
                </label>
              )}
            />
          ) : null}
          {showLinkAll && linkAll ? null : (
            <fieldset className="flex flex-col gap-2">
              <legend className="text-sm font-medium">Outros grupos</legend>
              <p className="text-sm text-muted-foreground">
                Este grupo entra sempre. Marque os outros em que a carta também
                fica.
              </p>
              {otherGroups.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  Você não está em outro grupo.
                </p>
              ) : (
                otherGroups.map((group) => (
                  <label
                    key={group.id}
                    className="flex items-center gap-2 text-sm"
                  >
                    <input
                      type="checkbox"
                      checked={groupIds.includes(group.id)}
                      onChange={(event) => {
                        const next = event.target.checked
                          ? [...groupIds, group.id]
                          : groupIds.filter((id) => id !== group.id)
                        form.setValue('groupIds', next)
                      }}
                    />
                    {group.name}
                  </label>
                ))
              )}
            </fieldset>
          )}
          <Button type="submit" disabled={mutation.isPending || !membersReady}>
            {mutation.isPending ? (
              <Loader2Icon className="animate-spin" />
            ) : null}
            Cadastrar
          </Button>
        </form>
      ) : (
        <CatalogSearch
          onSelect={(next) => {
            setCard(next)
          }}
        />
      )}
    </Dialog>
  )
}
