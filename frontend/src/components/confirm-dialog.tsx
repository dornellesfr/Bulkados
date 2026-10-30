import type { ReactNode } from 'react'

import { Dialog } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Loader2Icon } from 'lucide-react'

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  destructive = false,
  pending = false,
  onConfirm,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description: ReactNode
  confirmLabel: string
  destructive?: boolean
  pending?: boolean
  onConfirm: () => void
}) {
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!pending) {
          onOpenChange(next)
        }
      }}
      title={title}
      description={description}
    >
      <div className="flex justify-end gap-2">
        <Button
          type="button"
          variant="outline"
          disabled={pending}
          onClick={() => {
            onOpenChange(false)
          }}
        >
          Voltar
        </Button>
        <Button
          type="button"
          variant={destructive ? 'destructive' : 'default'}
          disabled={pending}
          onClick={onConfirm}
        >
          {pending ? <Loader2Icon className="animate-spin" /> : null}
          {confirmLabel}
        </Button>
      </div>
    </Dialog>
  )
}
