import { zodResolver } from '@hookform/resolvers/zod'
import { useQueryClient } from '@tanstack/react-query'
import { Link, useRouter } from '@tanstack/react-router'
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
import { login, loginInputSchema, meQueryOptions } from '@/lib/api/auth'
import type { LoginInput } from '@/lib/api/auth'
import { clearSession, hasSession } from '@/lib/auth/session'
import { safeInternalPath } from '@/lib/display'
import { applyApiFormError } from '@/lib/form-error'

export function LoginForm({ redirectTo }: { redirectTo?: string }) {
  const router = useRouter()
  const queryClient = useQueryClient()
  const form = useForm<LoginInput>({
    resolver: zodResolver(loginInputSchema),
    defaultValues: {
      identifier: '',
      password: '',
    },
  })

  return (
    <form
      className="flex flex-col gap-6"
      noValidate
      onSubmit={form.handleSubmit(async (values) => {
        try {
          queryClient.clear()
          await login(values)
          await queryClient.fetchQuery(meQueryOptions())
          await router.navigate({ href: safeInternalPath(redirectTo) })
        } catch (error) {
          if (hasSession()) {
            clearSession('expired')
          }
          applyApiFormError(form.setError, error, {
            password: 'password',
          })
        }
      })}
    >
      <FieldGroup>
        <Controller
          name="identifier"
          control={form.control}
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <FieldLabel htmlFor="login-identifier">Nick ou e-mail</FieldLabel>
              <Input
                {...field}
                id="login-identifier"
                autoComplete="username"
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
              <FieldLabel htmlFor="login-password">Senha</FieldLabel>
              <Input
                {...field}
                id="login-password"
                type="password"
                autoComplete="current-password"
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
        Entrar
      </Button>
      <div className="flex flex-wrap gap-x-4 gap-y-2 text-sm">
        <Link to="/cadastrar" className="underline-offset-4 hover:underline">
          Criar conta
        </Link>
        <Link
          to="/recuperar-senha"
          className="underline-offset-4 hover:underline"
        >
          Esqueci a senha
        </Link>
      </div>
    </form>
  )
}
