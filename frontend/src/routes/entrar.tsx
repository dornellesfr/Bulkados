import { redirect, createFileRoute } from '@tanstack/react-router'

import { LoginForm } from '@/components/auth/login-form'
import { PageHeader } from '@/components/layout/page-header'
import { parseEntrarSearch } from '@/lib/api/auth'
import { hasSession } from '@/lib/auth/session'

export const Route = createFileRoute('/entrar')({
  validateSearch: parseEntrarSearch,
  beforeLoad: () => {
    if (hasSession()) {
      throw redirect({ to: '/' })
    }
  },
  component: LoginPage,
})

function LoginPage() {
  const search = Route.useSearch()

  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-6">
      <PageHeader title="Entrar" />
      {search.aviso === 'conta-criada' ? (
        <p>Conta criada. Entre com seu nick ou e-mail.</p>
      ) : null}
      <LoginForm redirectTo={search.redirect} />
    </div>
  )
}
