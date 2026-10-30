import { redirect, createFileRoute } from '@tanstack/react-router'

import { AppShell } from '@/components/layout/app-shell'
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
  loader: ({ context }) =>
    context.queryClient.ensureQueryData(meQueryOptions()),
  component: AppShell,
})
