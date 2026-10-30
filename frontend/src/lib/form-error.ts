import type { FieldValues, Path, UseFormSetError } from 'react-hook-form'

import { apiErrorMessage } from '@/lib/api/client'

export function applyApiFormError<T extends FieldValues>(
  setError: UseFormSetError<T>,
  error: unknown,
  fields: {
    nick?: Path<T>
    password?: Path<T>
    email?: Path<T>
  },
) {
  const message = apiErrorMessage(error)
  const lower = message.toLocaleLowerCase('pt-BR')

  if (fields.nick && lower.includes('nick')) {
    setError(fields.nick, { message })
    return
  }

  if (fields.email && (lower.includes('e-mail') || lower.includes('email'))) {
    setError(fields.email, { message })
    return
  }

  if (
    fields.password &&
    (lower.includes('senha') || lower.includes('password'))
  ) {
    setError(fields.password, { message })
    return
  }

  setError('root', { message })
}
