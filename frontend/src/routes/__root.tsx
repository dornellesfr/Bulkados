import { Suspense } from 'react'
import { ReactQueryDevtoolsPanel } from '@tanstack/react-query-devtools'
import { TanStackDevtools } from '@tanstack/react-devtools'
import { Outlet, createRootRouteWithContext } from '@tanstack/react-router'
import { TanStackRouterDevtoolsPanel } from '@tanstack/react-router-devtools'

import { AppHeader } from '@/components/layout/app-header'
import { RoutePending } from '@/components/layout/route-state'
import { ThemeProvider } from '@/components/providers/theme-provider'
import { Toaster } from '@/components/ui/sonner'
import type { RouterContext } from '@/lib/router-context'

import '../styles.css'

export const Route = createRootRouteWithContext<RouterContext>()({
  component: RootComponent,
})

function RootComponent() {
  return (
    <ThemeProvider>
      <div className="flex min-h-svh flex-col">
        <AppHeader />
        <main className="flex w-full flex-1 flex-col px-4 py-8 sm:px-6 lg:px-8">
          <Suspense fallback={<RoutePending />}>
            <Outlet />
          </Suspense>
        </main>
      </div>
      <Toaster />
      {import.meta.env.DEV ? (
        <TanStackDevtools
          config={{
            position: 'bottom-right',
          }}
          plugins={[
            {
              name: 'TanStack Router',
              render: <TanStackRouterDevtoolsPanel />,
            },
            {
              name: 'TanStack Query',
              render: <ReactQueryDevtoolsPanel />,
            },
          ]}
        />
      ) : null}
    </ThemeProvider>
  )
}
