import { redirect, createFileRoute } from '@tanstack/react-router'

import { AuthFrame } from '@/components/auth/auth-frame'
import { ForgotPasswordForm } from '@/components/auth/forgot-password-form'
import { hasSession } from '@/lib/auth/session'

export const Route = createFileRoute('/recuperar-senha')({
  beforeLoad: () => {
    if (hasSession()) {
      throw redirect({ to: '/' })
    }
  },
  component: RecoverPage,
})

function RecoverPage() {
  return (
    <AuthFrame title="Recuperar senha" description="Informe o e-mail da conta.">
      <ForgotPasswordForm />
    </AuthFrame>
  )
}
