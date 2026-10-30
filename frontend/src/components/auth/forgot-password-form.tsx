import { useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { Link } from '@tanstack/react-router'
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
import { forgotPassword, forgotPasswordInputSchema } from '@/lib/api/auth'
import type { ForgotPasswordInput } from '@/lib/api/auth'
import { applyApiFormError } from '@/lib/form-error'

export function ForgotPasswordForm() {
  const [message, setMessage] = useState<string | null>(null)
  const form = useForm<ForgotPasswordInput>({
    resolver: zodResolver(forgotPasswordInputSchema),
    defaultValues: {
      identifier: '',
    },
  })
  const sent = message != null

  return (
    <form
      className="flex flex-col gap-6"
      noValidate
      onSubmit={form.handleSubmit(async (values) => {
        try {
          const nextMessage = await forgotPassword(values)
          setMessage(nextMessage)
        } catch (error) {
          applyApiFormError(form.setError, error, {})
        }
      })}
    >
      <FieldGroup>
        <Controller
          name="identifier"
          control={form.control}
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <FieldLabel htmlFor="forgot-identifier">
                Nick ou e-mail
              </FieldLabel>
              <Input
                {...field}
                id="forgot-identifier"
                autoComplete="username"
                disabled={sent}
                aria-invalid={fieldState.invalid}
              />
              {fieldState.invalid ? (
                <FieldError errors={[fieldState.error]} />
              ) : null}
            </Field>
          )}
        />
      </FieldGroup>
      {message ? <p>{message}</p> : null}
      {form.formState.errors.root ? (
        <p role="alert" className="text-sm text-destructive">
          {form.formState.errors.root.message}
        </p>
      ) : null}
      <Button type="submit" disabled={sent || form.formState.isSubmitting}>
        {form.formState.isSubmitting ? (
          <Loader2Icon className="animate-spin" />
        ) : null}
        Enviar
      </Button>
      <Link to="/entrar" className="text-sm underline-offset-4 hover:underline">
        Voltar para entrar
      </Link>
    </form>
  )
}
