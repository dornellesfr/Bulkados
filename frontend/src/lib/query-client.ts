import { QueryClient } from '@tanstack/react-query'

import { ApiError } from '@/lib/api/client'

export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60_000,
        retry: (failureCount, error) => {
          if (
            error instanceof ApiError &&
            [401, 404, 409, 422].includes(error.status)
          ) {
            return false
          }

          return failureCount < 1
        },
        refetchOnWindowFocus: false,
      },
    },
  })
}
