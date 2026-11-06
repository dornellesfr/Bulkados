import { redirect, createFileRoute } from '@tanstack/react-router'

import { AuthFrame } from '@/components/auth/auth-frame'
import { RegisterForm } from '@/components/auth/register-form'
import { hasSession } from '@/lib/auth/session'

export const Route = createFileRoute('/cadastrar')({
  beforeLoad: () => {
    if (hasSession()) {
      throw redirect({ to: '/' })
    }
  },
  component: RegisterPage,
})

function RegisterPage() {
  return (
    <AuthFrame title="Criar conta">
      <RegisterForm />
    </AuthFrame>
  )
}
