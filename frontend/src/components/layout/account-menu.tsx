import { useEffect, useId, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useRouterState } from '@tanstack/react-router'
import { MenuIcon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { clearSession } from '@/lib/auth/session'
import { cn } from '@/lib/utils'

const links = [
  {
    to: '/',
    label: 'Grupos',
    match: (path: string) => path === '/' || path.startsWith('/grupos'),
  },
  {
    to: '/perfil',
    label: 'Perfil',
    match: (path: string) => path === '/perfil',
  },
] as const

export function AccountMenu() {
  const [open, setOpen] = useState(false)
  const panelId = useId()
  const rootRef = useRef<HTMLDivElement>(null)
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  })

  useEffect(() => {
    setOpen(false)
  }, [pathname])

  useEffect(() => {
    if (!open) {
      return
    }

    function onPointerDown(event: PointerEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false)
      }
    }

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setOpen(false)
      }
    }

    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  return (
    <div className="relative" ref={rootRef}>
      <Button
        type="button"
        variant="outline"
        size="icon"
        aria-label={open ? 'Fechar menu' : 'Abrir menu'}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => {
          setOpen((current) => !current)
        }}
      >
        <MenuIcon />
      </Button>
      {open ? (
        <nav
          id={panelId}
          className="absolute top-full left-0 z-30 mt-2 w-44 border bg-background py-1"
        >
          {links.map((item) => {
            const current = item.match(pathname)
            return (
              <Link
                key={item.to}
                to={item.to}
                aria-current={current ? 'page' : undefined}
                className={cn(
                  'block px-3 py-2 text-sm outline-none focus-visible:bg-muted',
                  current ? 'bg-muted' : 'hover:bg-muted',
                )}
              >
                {item.label}
              </Link>
            )
          })}
          <button
            type="button"
            className="block w-full border-t px-3 py-2 text-left text-sm outline-none hover:bg-muted focus-visible:bg-muted"
            onClick={() => {
              clearSession('logout')
              queryClient.clear()
              void navigate({ to: '/entrar' })
            }}
          >
            Sair
          </button>
        </nav>
      ) : null}
    </div>
  )
}
