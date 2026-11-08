import type { FieldValues, Path, UseFormSetError } from 'react-hook-form'

import { apiErrorMessage } from '@/lib/api/client'

export function applyApiFormError<T extends FieldValues>(
  setError: UseFormSetError<T>,
  error: unknown,
  fields: {
    email?: Path<T>
    password?: Path<T>
    currentPassword?: Path<T>
    newPassword?: Path<T>
    firstName?: Path<T>
    lastName?: Path<T>
  },
) {
  const message = apiErrorMessage(error)
  const lower = message.toLocaleLowerCase('pt-BR')

  if (fields.lastName && lower.includes('sobrenome')) {
    setError(fields.lastName, { message })
    return
  }

  if (fields.firstName && lower.includes('nome')) {
    setError(fields.firstName, { message })
    return
  }

  if (
    fields.email &&
    (lower.includes('e-mail') ||
      lower.includes('email') ||
      lower.includes('convid'))
  ) {
    setError(fields.email, { message })
    return
  }

  if (fields.currentPassword && lower.includes('senha atual')) {
    setError(fields.currentPassword, { message })
    return
  }

  if (fields.newPassword && lower.includes('nova senha')) {
    setError(fields.newPassword, { message })
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
