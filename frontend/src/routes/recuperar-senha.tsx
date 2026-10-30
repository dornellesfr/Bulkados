import { redirect, createFileRoute } from '@tanstack/react-router'

import { ForgotPasswordForm } from '@/components/auth/forgot-password-form'
import { PageHeader } from '@/components/layout/page-header'
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
    <div className="mx-auto flex w-full max-w-md flex-col gap-6">
      <PageHeader
        title="Recuperar senha"
        description="Informe o nick ou o e-mail da conta."
      />
      <ForgotPasswordForm />
    </div>
  )
}
