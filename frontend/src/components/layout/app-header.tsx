import { Link, useMatchRoute } from '@tanstack/react-router'

import { AccountMenu } from '@/components/layout/account-menu'
import { ThemeToggle } from '@/components/layout/theme-toggle'
import { useSession } from '@/lib/auth/session'

export function AppHeader() {
  const session = useSession()
  const matchRoute = useMatchRoute()
  const signedIn = session.status === 'in'
  const isDeckPage = matchRoute({
    to: '/grupos/$groupId/decks/$deckId',
    fuzzy: true,
  })

  if (signedIn && isDeckPage) {
    return null
  }

  return (
    <header className="border-b bg-background">
      <div className="flex w-full items-center gap-3 px-4 py-3 sm:px-6 lg:px-8">
        {signedIn ? <AccountMenu /> : null}
        <Link
          to={signedIn ? '/' : '/entrar'}
          className="font-heading text-xl leading-none font-medium tracking-tight"
        >
          bulkados
        </Link>
        <div className="ml-auto">
          <ThemeToggle />
        </div>
      </div>
    </header>
  )
}
