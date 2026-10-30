import { redirect, createFileRoute } from '@tanstack/react-router'

import { RegisterForm } from '@/components/auth/register-form'
import { PageHeader } from '@/components/layout/page-header'
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
    <div className="mx-auto flex w-full max-w-md flex-col gap-6">
      <PageHeader title="Cadastrar" />
      <RegisterForm />
    </div>
  )
}
