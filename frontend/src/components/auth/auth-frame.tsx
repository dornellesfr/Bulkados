import type { ReactNode } from 'react'

export function AuthFrame({
  title,
  description,
  notice,
  children,
}: {
  title: string
  description?: string
  notice?: string
  children: ReactNode
}) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center py-6">
      <div className="flex w-full max-w-sm flex-col gap-8">
        <div className="flex flex-col gap-2">
          <h1 className="font-heading text-3xl font-medium tracking-tight">
            {title}
          </h1>
          {description ? (
            <p className="text-sm text-muted-foreground">{description}</p>
          ) : null}
          {notice ? <p className="text-sm">{notice}</p> : null}
        </div>
        {children}
      </div>
    </div>
  )
}
