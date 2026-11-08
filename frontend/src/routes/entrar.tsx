import { redirect, createFileRoute } from '@tanstack/react-router'

import { AuthFrame } from '@/components/auth/auth-frame'
import { LoginForm } from '@/components/auth/login-form'
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
    <AuthFrame
      title="Entrar"
      notice={
        search.aviso === 'conta-criada'
          ? 'Conta criada. Entre com seu e-mail.'
          : undefined
      }
    >
      <LoginForm redirectTo={search.redirect} />
    </AuthFrame>
  )
}
