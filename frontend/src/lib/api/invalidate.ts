import type { QueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { ApiError, apiErrorMessage } from '@/lib/api/client'

export async function invalidateBoard(queryClient: QueryClient) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ['copies'] }),
    queryClient.invalidateQueries({ queryKey: ['decks'] }),
    queryClient.invalidateQueries({ queryKey: ['handoffs'] }),
  ])
}

export async function invalidateMembership(queryClient: QueryClient) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ['groups'] }),
    queryClient.invalidateQueries({ queryKey: ['invitations'] }),
  ])
}

export function toastError(error: unknown) {
  toast.error(apiErrorMessage(error))
}

export async function reportBoardError(
  queryClient: QueryClient,
  error: unknown,
) {
  toastError(error)

  if (error instanceof ApiError && error.status !== 401 && error.status !== 0) {
    await invalidateBoard(queryClient)
  }
}
