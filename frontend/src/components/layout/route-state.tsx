import { useEffect } from 'react'
import {
  isCancelledError,
  useQueryErrorResetBoundary,
} from '@tanstack/react-query'
import { Link, useRouter } from '@tanstack/react-router'
import type { ErrorComponentProps } from '@tanstack/react-router'

import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'

export function RoutePending() {
  return (
    <div className="flex flex-col gap-4" aria-busy="true" aria-live="polite">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-4 w-72" />
      <div className="flex flex-col gap-3">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-20 w-full" />
      </div>
    </div>
  )
}

export function RouteError({ error, reset }: ErrorComponentProps) {
  const router = useRouter()
  const queryErrorResetBoundary = useQueryErrorResetBoundary()

  useEffect(() => {
    queryErrorResetBoundary.reset()
  }, [queryErrorResetBoundary])

  const message = isCancelledError(error)
    ? 'Não foi possível concluir. Tente de novo.'
    : error instanceof Error
      ? error.message
      : 'Algo deu errado ao carregar a página.'

  return (
    <div className="flex max-w-lg flex-col gap-4 rounded-xl bg-card p-6 ring-1 ring-foreground/10">
      <div>
        <h1 className="font-heading text-lg font-medium">
          Não foi possível carregar
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">{message}</p>
      </div>
      <div className="flex gap-2">
        <Button
          type="button"
          onClick={() => {
            reset()
            void router.invalidate()
          }}
        >
          Tentar de novo
        </Button>
        <Button type="button" variant="outline" asChild>
          <Link to="/">Ir para o início</Link>
        </Button>
      </div>
    </div>
  )
}

export function NotFound() {
  return (
    <div className="flex max-w-lg flex-col gap-4">
      <div>
        <h1 className="font-heading text-lg font-medium">
          Página não encontrada
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          O endereço não corresponde a nenhuma rota da aplicação.
        </p>
      </div>
      <Button type="button" variant="outline" className="w-fit" asChild>
        <Link to="/">Ir para o início</Link>
      </Button>
    </div>
  )
}
