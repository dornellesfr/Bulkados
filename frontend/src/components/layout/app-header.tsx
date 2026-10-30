import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from '@tanstack/react-router'

import { ThemeToggle } from '@/components/layout/theme-toggle'
import { Button } from '@/components/ui/button'
import { meQueryOptions } from '@/lib/api/auth'
import { clearSession, useSession } from '@/lib/auth/session'

export function AppHeader() {
  const session = useSession()
  const signedIn = session.status === 'in'
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const me = useQuery({
    ...meQueryOptions(),
    enabled: signedIn,
  })

  return (
    <header className="border-b bg-background">
      <div className="mx-auto flex w-full max-w-5xl items-center gap-3 px-4 py-3">
        <Link
          to={signedIn ? '/' : '/entrar'}
          className="font-heading text-sm font-semibold tracking-tight"
        >
          Magic Bulk
        </Link>
        <div className="ml-auto flex items-center gap-2">
          {signedIn ? (
            <>
              <span className="max-w-40 truncate text-sm">{me.data?.nick}</span>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  clearSession('logout')
                  queryClient.clear()
                  void navigate({ to: '/entrar' })
                }}
              >
                Sair
              </Button>
            </>
          ) : null}
          <ThemeToggle />
        </div>
      </div>
    </header>
  )
}
