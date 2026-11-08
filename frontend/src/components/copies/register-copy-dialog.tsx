import { useEffect, useRef, useState } from 'react'
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

import { CardThumb } from '@/components/cards/card-thumb'
import { CardTitle } from '@/components/cards/card-title'
import { CatalogSearch } from '@/components/copies/catalog-search'
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
import { NativeSelect } from '@/components/ui/native-select'
import type { CatalogCard } from '@/lib/api/catalog'
import { createCopies } from '@/lib/api/copies'
import { addDeckCopies, decksQueryOptions } from '@/lib/api/decks'
import { groupsQueryOptions, membersQueryOptions } from '@/lib/api/groups'
import type { Group, Member } from '@/lib/api/groups'
import { invalidateBoard, toastError } from '@/lib/api/invalidate'
import { personName, quantitySchema } from '@/lib/api/schemas'

const formSchema = z
  .object({
    quantity: quantitySchema,
    holderId: z.string(),
    groupIds: z.array(z.string()),
    deckId: z.string(),
  })
  .superRefine((values, ctx) => {
    if (values.deckId) {
      return
    }

    if (!values.holderId) {
      ctx.addIssue({
        code: 'custom',
        path: ['holderId'],
        message: 'Escolha a casa.',
      })
    }

    if (values.groupIds.length === 0) {
      ctx.addIssue({
        code: 'custom',
        path: ['groupIds'],
        message: 'Escolha ao menos um grupo.',
      })
    }
  })

type FormValues = z.infer<typeof formSchema>

function acceptedMembers(members: Array<Member>) {
  return members.filter((member) => member.status === 'accepted')
}

function acceptedIntersection(lists: Array<Array<Member>>) {
  if (lists.length === 0) {
    return []
  }

  const [first, ...rest] = lists

  return acceptedMembers(first).filter((member) =>
    rest.every((list) =>
      list.some(
        (item) => item.user_id === member.user_id && item.status === 'accepted',
      ),
    ),
  )
}

function groupsForHolder(
  groups: Array<Group>,
  membersByGroup: Map<string, Array<Member>>,
  holderId: string,
) {
  return groups.filter((group) =>
    acceptedMembers(membersByGroup.get(group.id) ?? []).some(
      (member) => member.user_id === holderId,
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
  const seeded = useRef(false)
  const [card, setCard] = useState<CatalogCard | null>(null)
  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      quantity: 1,
      holderId: meId,
      groupIds: [groupId],
      deckId: '',
    },
  })
  const holderId = form.watch('holderId')
  const groupIds = form.watch('groupIds')
  const deckId = form.watch('deckId')
  const groups = useQuery({
    ...groupsQueryOptions(),
    enabled: open,
  })
  const decks = useQuery({
    ...decksQueryOptions(),
    enabled: open,
  })
  const myDecks = decks.data ?? []
  const allGroups = groups.data ?? []
  const memberQueries = useQueries({
    queries: allGroups.map((group) => ({
      ...membersQueryOptions(group.id),
      enabled: open,
    })),
  })
  const membersReady =
    allGroups.length > 0 && memberQueries.every((query) => query.isSuccess)
  const membersByGroup = new Map(
    allGroups.map((group, index) => [
      group.id,
      memberQueries[index]?.data ?? [],
    ]),
  )
  const holderGroups = membersReady
    ? groupsForHolder(allGroups, membersByGroup, holderId)
    : allGroups
  const scopeIds = groupIds.length > 0 ? groupIds : [groupId]
  const holders = membersReady
    ? acceptedIntersection(scopeIds.map((id) => membersByGroup.get(id) ?? []))
    : []
  const allHolderGroupsSelected =
    holderGroups.length > 0 &&
    holderGroups.every((group) => groupIds.includes(group.id))

  useEffect(() => {
    if (!open) {
      seeded.current = false
      return
    }

    if (!groups.isSuccess || seeded.current) {
      return
    }

    seeded.current = true
    form.setValue(
      'groupIds',
      groups.data.map((group) => group.id),
    )
  }, [form, groups.data, groups.isSuccess, open])

  useEffect(() => {
    if (!open || !membersReady) {
      return
    }

    if (holders.some((member) => member.user_id === holderId)) {
      return
    }

    form.setValue('holderId', meId)
  }, [form, holderId, holders, meId, membersReady, open])

  function selectGroups(next: Array<string>) {
    form.setValue('groupIds', next, {
      shouldValidate: form.formState.isSubmitted,
    })
  }

  const mutation = useMutation({
    mutationFn: () => {
      const values = form.getValues()

      if (values.deckId) {
        return addDeckCopies(values.deckId, {
          oracle_id: card?.oracle_id ?? '',
          quantity: values.quantity,
        })
      }

      return createCopies(groupId, {
        oracle_id: card?.oracle_id ?? '',
        quantity: values.quantity,
        ...(values.holderId !== meId ? { holder_id: values.holderId } : {}),
        group_ids: values.groupIds,
      })
    },
    onSuccess: async () => {
      await invalidateBoard(queryClient)
      setCard(null)
      form.reset({
        quantity: 1,
        holderId: meId,
        groupIds: allGroups.map((group) => group.id),
        deckId: '',
      })
      onOpenChange(false)
    },
    onError: (error) => {
      toastError(error)
    },
  })

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
            groupIds: [groupId],
            deckId: '',
          })
        }

        onOpenChange(next)
      }}
      title="Cadastrar carta"
      description="Livre no bulk, qualquer um pode solicitar e você decide se aceita. Num deck seu, ela entra na hora e não fica travada."
    >
      {card ? (
        <form
          className="flex flex-col gap-4"
          noValidate
          onSubmit={form.handleSubmit(() => mutation.mutateAsync())}
        >
          <div className="flex items-start gap-3">
            <CardThumb
              url={card.image_url}
              className="aspect-[488/680] h-auto w-32 cursor-zoom-in rounded-lg ring-1 ring-foreground/10"
            />
            <div className="flex min-w-0 flex-1 items-start justify-between gap-3">
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
              name="deckId"
              control={form.control}
              render={({ field }) => (
                <Field>
                  <FieldLabel htmlFor="copy-destination">Onde entra</FieldLabel>
                  <NativeSelect
                    id="copy-destination"
                    value={field.value}
                    disabled={decks.isPending}
                    onChange={(event) => {
                      field.onChange(event.target.value)
                    }}
                  >
                    <option value="">Livre no bulk</option>
                    {myDecks.map((deck) => (
                      <option key={deck.id} value={deck.id}>
                        No deck {deck.name}
                      </option>
                    ))}
                  </NativeSelect>
                  <FieldDescription>
                    {field.value
                      ? 'Entra nesse deck, na sua casa, sem travar. Se você já tem essa carta livre no bulk, essa cópia é a que entra.'
                      : myDecks.length === 0 && decks.isSuccess
                        ? 'Qualquer pessoa do grupo pode solicitar, e você decide se aceita. Crie um deck para ela já entrar com você.'
                        : 'Qualquer pessoa do grupo pode solicitar, e você decide se aceita.'}
                  </FieldDescription>
                </Field>
              )}
            />
            {deckId ? null : (
              <>
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
                          if (!membersReady) {
                            return
                          }
                          selectGroups(
                            groupsForHolder(
                              allGroups,
                              membersByGroup,
                              next,
                            ).map((group) => group.id),
                          )
                        }}
                        disabled={!membersReady}
                        aria-invalid={fieldState.invalid}
                      >
                        {holders.map((member) => (
                          <option key={member.user_id} value={member.user_id}>
                            {personName(member)}
                          </option>
                        ))}
                      </NativeSelect>
                      {fieldState.invalid ? (
                        <FieldError errors={[fieldState.error]} />
                      ) : null}
                    </Field>
                  )}
                />
                <Controller
                  name="groupIds"
                  control={form.control}
                  render={({ fieldState }) => (
                    <Field data-invalid={fieldState.invalid}>
                      <FieldLabel>Grupos</FieldLabel>
                      <div className="flex flex-col gap-2 rounded-lg border border-input p-3">
                        <label className="flex items-center gap-2 text-sm">
                          <input
                            type="checkbox"
                            checked={allHolderGroupsSelected}
                            disabled={
                              !membersReady || holderGroups.length === 0
                            }
                            onChange={(event) => {
                              selectGroups(
                                event.target.checked
                                  ? holderGroups.map((group) => group.id)
                                  : [],
                              )
                            }}
                          />
                          Todos
                        </label>
                        {holderGroups.map((group) => (
                          <label
                            key={group.id}
                            className="flex items-center gap-2 text-sm"
                          >
                            <input
                              type="checkbox"
                              checked={groupIds.includes(group.id)}
                              disabled={!membersReady}
                              onChange={(event) => {
                                const next = event.target.checked
                                  ? [...groupIds, group.id]
                                  : groupIds.filter((id) => id !== group.id)
                                selectGroups(next)
                              }}
                            />
                            {group.name}
                          </label>
                        ))}
                      </div>
                      {fieldState.invalid ? (
                        <FieldError errors={[fieldState.error]} />
                      ) : (
                        <p className="text-sm text-muted-foreground">
                          Marque onde essa carta fica.
                        </p>
                      )}
                    </Field>
                  )}
                />
              </>
            )}
          </FieldGroup>
          <Button
            type="submit"
            disabled={mutation.isPending || (!deckId && !membersReady)}
          >
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
