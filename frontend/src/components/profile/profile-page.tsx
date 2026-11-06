import { useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useQueryClient, useSuspenseQuery } from '@tanstack/react-query'
import { Loader2Icon } from 'lucide-react'
import { Controller, useForm } from 'react-hook-form'

import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import {
  authKeys,
  changePassword,
  changePasswordInputSchema,
  meQueryOptions,
  profileInputSchema,
  updateProfile,
} from '@/lib/api/auth'
import type { ChangePasswordInput, ProfileInput } from '@/lib/api/auth'
import { applyApiFormError } from '@/lib/form-error'

const createdAtFormat = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'long' })

export function ProfilePage() {
  const queryClient = useQueryClient()
  const { data: me } = useSuspenseQuery(meQueryOptions())
  const [saved, setSaved] = useState(false)
  const [nameSaved, setNameSaved] = useState(false)
  const nameForm = useForm<ProfileInput>({
    resolver: zodResolver(profileInputSchema),
    defaultValues: {
      first_name: me.first_name,
      last_name: me.last_name,
    },
  })
  const form = useForm<ChangePasswordInput>({
    resolver: zodResolver(changePasswordInputSchema),
    defaultValues: {
      current_password: '',
      new_password: '',
      confirm_password: '',
    },
  })
  const createdAt = createdAtFormat.format(new Date(me.created_at))

  return (
    <div className="mx-auto flex w-full max-w-sm flex-col gap-10">
      <PageHeader title="Perfil" />
      <div className="flex flex-col gap-10">
        <form
          className="flex flex-col gap-6"
          noValidate
          onSubmit={nameForm.handleSubmit(async (values) => {
            try {
              const next = await updateProfile(values)
              queryClient.setQueryData(authKeys.me, next)
              setNameSaved(true)
            } catch (error) {
              setNameSaved(false)
              applyApiFormError(nameForm.setError, error, {
                firstName: 'first_name',
                lastName: 'last_name',
              })
            }
          })}
        >
          <FieldGroup>
            <Controller
              name="first_name"
              control={nameForm.control}
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor="profile-first-name">Nome</FieldLabel>
                  <Input
                    {...field}
                    id="profile-first-name"
                    autoComplete="given-name"
                    className="h-10"
                    aria-invalid={fieldState.invalid}
                    onChange={(event) => {
                      setNameSaved(false)
                      field.onChange(event)
                    }}
                  />
                  {fieldState.invalid ? (
                    <FieldError errors={[fieldState.error]} />
                  ) : null}
                </Field>
              )}
            />
            <Controller
              name="last_name"
              control={nameForm.control}
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor="profile-last-name">
                    Sobrenome
                  </FieldLabel>
                  <Input
                    {...field}
                    id="profile-last-name"
                    autoComplete="family-name"
                    className="h-10"
                    aria-invalid={fieldState.invalid}
                    onChange={(event) => {
                      setNameSaved(false)
                      field.onChange(event)
                    }}
                  />
                  {fieldState.invalid ? (
                    <FieldError errors={[fieldState.error]} />
                  ) : null}
                </Field>
              )}
            />
          </FieldGroup>
          {nameForm.formState.errors.root ? (
            <p role="alert" className="text-sm text-destructive">
              {nameForm.formState.errors.root.message}
            </p>
          ) : null}
          {nameSaved ? <p>Nome salvo.</p> : null}
          <Button
            type="submit"
            className="h-10"
            disabled={nameForm.formState.isSubmitting}
          >
            {nameForm.formState.isSubmitting ? (
              <Loader2Icon className="animate-spin" />
            ) : null}
            Salvar nome
          </Button>
        </form>
        <div className="flex flex-col gap-1">
          <p className="text-sm text-muted-foreground">E-mail</p>
          <p className="break-all">{me.email}</p>
          <p className="mt-3 text-sm text-muted-foreground">
            Conta criada em {createdAt}.
          </p>
        </div>
        <form
          className="flex flex-col gap-6"
          noValidate
          onSubmit={form.handleSubmit(async (values) => {
            try {
              await changePassword(values)
              form.reset()
              setSaved(true)
            } catch (error) {
              setSaved(false)
              applyApiFormError(form.setError, error, {
                currentPassword: 'current_password',
                newPassword: 'new_password',
              })
            }
          })}
        >
          <h2 className="font-heading text-xl font-medium">Trocar senha</h2>
          <FieldGroup>
            <Controller
              name="current_password"
              control={form.control}
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor="current-password">
                    Senha atual
                  </FieldLabel>
                  <Input
                    {...field}
                    id="current-password"
                    type="password"
                    autoComplete="current-password"
                    className="h-10"
                    aria-invalid={fieldState.invalid}
                    onChange={(event) => {
                      setSaved(false)
                      field.onChange(event)
                    }}
                  />
                  {fieldState.invalid ? (
                    <FieldError errors={[fieldState.error]} />
                  ) : null}
                </Field>
              )}
            />
            <Controller
              name="new_password"
              control={form.control}
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor="new-password">Nova senha</FieldLabel>
                  <Input
                    {...field}
                    id="new-password"
                    type="password"
                    autoComplete="new-password"
                    className="h-10"
                    aria-invalid={fieldState.invalid}
                    onChange={(event) => {
                      setSaved(false)
                      field.onChange(event)
                    }}
                  />
                  {fieldState.invalid ? (
                    <FieldError errors={[fieldState.error]} />
                  ) : (
                    <FieldDescription>
                      Pelo menos 6 caracteres.
                    </FieldDescription>
                  )}
                </Field>
              )}
            />
            <Controller
              name="confirm_password"
              control={form.control}
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor="confirm-password">
                    Confirmar nova senha
                  </FieldLabel>
                  <Input
                    {...field}
                    id="confirm-password"
                    type="password"
                    autoComplete="new-password"
                    className="h-10"
                    aria-invalid={fieldState.invalid}
                    onChange={(event) => {
                      setSaved(false)
                      field.onChange(event)
                    }}
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
          {saved ? <p>Senha salva.</p> : null}
          <Button
            type="submit"
            className="h-10"
            disabled={form.formState.isSubmitting}
          >
            {form.formState.isSubmitting ? (
              <Loader2Icon className="animate-spin" />
            ) : null}
            Salvar senha
          </Button>
        </form>
      </div>
    </div>
  )
}
