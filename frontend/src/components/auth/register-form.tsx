import { zodResolver } from '@hookform/resolvers/zod'
import { useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from '@tanstack/react-router'
import { Loader2Icon } from 'lucide-react'
import { Controller, useForm } from 'react-hook-form'

import { Button } from '@/components/ui/button'
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { meQueryOptions, register, registerInputSchema } from '@/lib/api/auth'
import type { RegisterInput } from '@/lib/api/auth'
import { clearSession, hasSession } from '@/lib/auth/session'
import { applyApiFormError } from '@/lib/form-error'

export function RegisterForm() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const form = useForm<RegisterInput>({
    resolver: zodResolver(registerInputSchema),
    defaultValues: {
      email: '',
      password: '',
      nick: '',
    },
  })

  return (
    <form
      className="flex flex-col gap-6"
      noValidate
      onSubmit={form.handleSubmit(async (values) => {
        try {
          queryClient.clear()
          const result = await register(values)

          if (!result.session) {
            await navigate({
              to: '/entrar',
              search: { aviso: 'conta-criada' },
            })
            return
          }

          await queryClient.fetchQuery(meQueryOptions())
          await navigate({ to: '/' })
        } catch (error) {
          if (hasSession()) {
            clearSession('expired')
          }
          applyApiFormError(form.setError, error, {
            email: 'email',
            password: 'password',
            nick: 'nick',
          })
        }
      })}
    >
      <FieldGroup>
        <Controller
          name="email"
          control={form.control}
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <FieldLabel htmlFor="register-email">E-mail</FieldLabel>
              <Input
                {...field}
                id="register-email"
                type="email"
                autoComplete="email"
                aria-invalid={fieldState.invalid}
              />
              {fieldState.invalid ? (
                <FieldError errors={[fieldState.error]} />
              ) : null}
            </Field>
          )}
        />
        <Controller
          name="password"
          control={form.control}
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <FieldLabel htmlFor="register-password">Senha</FieldLabel>
              <Input
                {...field}
                id="register-password"
                type="password"
                autoComplete="new-password"
                aria-invalid={fieldState.invalid}
              />
              {fieldState.invalid ? (
                <FieldError errors={[fieldState.error]} />
              ) : null}
            </Field>
          )}
        />
        <Controller
          name="nick"
          control={form.control}
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <FieldLabel htmlFor="register-nick">Nick</FieldLabel>
              <Input
                {...field}
                id="register-nick"
                autoComplete="username"
                aria-invalid={fieldState.invalid}
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
      <Button type="submit" disabled={form.formState.isSubmitting}>
        {form.formState.isSubmitting ? (
          <Loader2Icon className="animate-spin" />
        ) : null}
        Cadastrar
      </Button>
      <Link to="/entrar" className="text-sm underline-offset-4 hover:underline">
        Já tenho conta
      </Link>
    </form>
  )
}
