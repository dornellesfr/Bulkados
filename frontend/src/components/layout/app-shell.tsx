import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Outlet, useNavigate, useRouter } from '@tanstack/react-router'

import { useSession } from '@/lib/auth/session'

export function AppShell() {
  const session = useSession()
  const navigate = useNavigate()
  const router = useRouter()
  const queryClient = useQueryClient()

  useEffect(() => {
    if (session.status !== 'out' || session.reason !== 'expired') {
      return
    }

    const redirect = router.state.location.href
    queryClient.clear()
    void navigate({
      to: '/entrar',
      search: { redirect },
    })
  }, [navigate, queryClient, router, session])

  if (session.status !== 'in') {
    return null
  }

  return <Outlet />
}
