import { useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient, useSuspenseQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { Controller, useForm } from 'react-hook-form'
import { Loader2Icon } from 'lucide-react'

import { ConfirmDialog } from '@/components/confirm-dialog'
import { PageHeader } from '@/components/layout/page-header'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { meQueryOptions } from '@/lib/api/auth'
import {
  groupNameInputSchema,
  groupsQueryOptions,
  inviteInputSchema,
  inviteMember,
  leaveGroup,
  membersQueryOptions,
  renameGroup,
} from '@/lib/api/groups'
import type { GroupNameInput, InviteInput } from '@/lib/api/groups'
import {
  invalidateBoard,
  invalidateMembership,
  toastError,
} from '@/lib/api/invalidate'
import { applyApiFormError } from '@/lib/form-error'

export function MembersPage({ groupId }: { groupId: string }) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { data: me } = useSuspenseQuery(meQueryOptions())
  const { data: groups } = useSuspenseQuery(groupsQueryOptions())
  const { data: members } = useSuspenseQuery(membersQueryOptions(groupId))
  const group = groups.find((item) => item.id === groupId)
  const isOwner = group?.owner_id === me.id
  const [renameOpen, setRenameOpen] = useState(false)
  const [leaveOpen, setLeaveOpen] = useState(false)

  const inviteForm = useForm<InviteInput>({
    resolver: zodResolver(inviteInputSchema),
    defaultValues: { nick: '' },
  })

  const invite = useMutation({
    mutationFn: (values: InviteInput) => inviteMember(groupId, values),
    onSuccess: async () => {
      inviteForm.reset()
      await invalidateMembership(queryClient)
    },
    onError: (error) => {
      applyApiFormError(inviteForm.setError, error, { nick: 'nick' })
    },
  })

  const renameForm = useForm<GroupNameInput>({
    resolver: zodResolver(groupNameInputSchema),
    values: { name: group?.name ?? '' },
  })

  const rename = useMutation({
    mutationFn: (values: GroupNameInput) => renameGroup(groupId, values),
    onSuccess: async () => {
      setRenameOpen(false)
      await invalidateMembership(queryClient)
    },
    onError: (error) => {
      applyApiFormError(renameForm.setError, error, {})
    },
  })

  const leave = useMutation({
    mutationFn: () => leaveGroup(groupId),
    onSuccess: async () => {
      await invalidateMembership(queryClient)
      await invalidateBoard(queryClient)
      await navigate({ to: '/' })
    },
    onError: (error) => {
      toastError(error)
    },
  })

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Membros"
        action={
          isOwner ? (
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setRenameOpen(true)
              }}
            >
              Renomear
            </Button>
          ) : null
        }
      />
      <form
        className="flex max-w-xl flex-col gap-4"
        noValidate
        onSubmit={inviteForm.handleSubmit((values) =>
          invite.mutateAsync(values),
        )}
      >
        <FieldGroup>
          <Controller
            name="nick"
            control={inviteForm.control}
            render={({ field, fieldState }) => (
              <Field data-invalid={fieldState.invalid}>
                <FieldLabel htmlFor="invite-nick">Nick</FieldLabel>
                <Input
                  {...field}
                  id="invite-nick"
                  aria-invalid={fieldState.invalid}
                />
                {fieldState.invalid ? (
                  <FieldError errors={[fieldState.error]} />
                ) : null}
              </Field>
            )}
          />
        </FieldGroup>
        {inviteForm.formState.errors.root ? (
          <p role="alert" className="text-sm text-destructive">
            {inviteForm.formState.errors.root.message}
          </p>
        ) : null}
        <Button type="submit" className="w-fit" disabled={invite.isPending}>
          {invite.isPending ? <Loader2Icon className="animate-spin" /> : null}
          Convidar
        </Button>
      </form>
      <ul className="flex flex-col gap-3">
        {members.map((member) => (
          <li
            key={member.user_id}
            className="flex items-center justify-between gap-3 rounded-xl bg-card p-4 ring-1 ring-foreground/10"
          >
            <span className="font-medium">{member.nick}</span>
            <span className="flex gap-2">
              {group?.owner_id === member.user_id ? <Badge>Dono</Badge> : null}
              {member.status === 'invited' ? (
                <Badge variant="secondary">Convidado</Badge>
              ) : null}
            </span>
          </li>
        ))}
      </ul>
      <Button
        type="button"
        variant="destructive"
        className="w-fit"
        onClick={() => {
          setLeaveOpen(true)
        }}
      >
        Sair do grupo
      </Button>
      <Dialog
        open={renameOpen}
        onOpenChange={setRenameOpen}
        title="Renomear grupo"
      >
        <form
          className="flex flex-col gap-4"
          noValidate
          onSubmit={renameForm.handleSubmit((values) =>
            rename.mutateAsync(values),
          )}
        >
          <FieldGroup>
            <Controller
              name="name"
              control={renameForm.control}
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor="rename-group">Nome</FieldLabel>
                  <Input
                    {...field}
                    id="rename-group"
                    aria-invalid={fieldState.invalid}
                  />
                  {fieldState.invalid ? (
                    <FieldError errors={[fieldState.error]} />
                  ) : null}
                </Field>
              )}
            />
          </FieldGroup>
          {renameForm.formState.errors.root ? (
            <p role="alert" className="text-sm text-destructive">
              {renameForm.formState.errors.root.message}
            </p>
          ) : null}
          <Button type="submit" disabled={rename.isPending}>
            {rename.isPending ? (
              <Loader2Icon className="animate-spin" />
            ) : null}
            Salvar
          </Button>
        </form>
      </Dialog>
      <ConfirmDialog
        open={leaveOpen}
        onOpenChange={setLeaveOpen}
        title="Sair do grupo"
        confirmLabel="Sair"
        destructive
        pending={leave.isPending}
        onConfirm={() => {
          leave.mutate()
        }}
        description={
          <ul className="list-disc space-y-1 pl-4">
            <li>Os decks de quem sai neste grupo são apagados.</li>
            <li>
              Carta desses decks que está na casa de outra pessoa volta ao
              bulk, livre.
            </li>
            <li>
              Carta na casa de quem sai deixa este grupo e continua nos outros
              grupos em que já estava.
            </li>
            <li>
              Se quem sai é o dono e ainda há gente, o membro accepted mais
              antigo fica dono.
            </li>
            <li>Se era a última pessoa, o grupo acaba.</li>
          </ul>
        }
      />
    </div>
  )
}
