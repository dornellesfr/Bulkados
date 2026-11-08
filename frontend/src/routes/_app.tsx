import { redirect, createFileRoute } from '@tanstack/react-router'

import { AppShell } from '@/components/layout/app-shell'
import { ApiError } from '@/lib/api/client'
import { meQueryOptions } from '@/lib/api/auth'
import { hasSession } from '@/lib/auth/session'

export const Route = createFileRoute('/_app')({
  beforeLoad: ({ location }) => {
    if (!hasSession()) {
      throw redirect({
        to: '/entrar',
        search: { redirect: location.href },
      })
    }
  },
  loader: async ({ context, location }) => {
    try {
      await context.queryClient.ensureQueryData(meQueryOptions())
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        throw redirect({
          to: '/entrar',
          search: { redirect: location.href },
        })
      }

      throw error
    }
  },
  component: AppShell,
})
