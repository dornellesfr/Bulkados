import { useEffect, useId, useRef } from 'react'
import type { ReactNode } from 'react'
import { XIcon } from 'lucide-react'

import { Button } from '@/components/ui/button'

export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  children,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description?: ReactNode
  children: ReactNode
}) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const titleId = useId()

  useEffect(() => {
    const dialog = dialogRef.current

    if (!dialog) {
      return
    }

    if (open && !dialog.open) {
      dialog.showModal()
    } else if (!open && dialog.open) {
      dialog.close()
    }
  }, [open])

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={titleId}
      className="m-0 h-full max-h-none w-full max-w-none bg-transparent p-4 backdrop:bg-black/40"
      onClose={() => {
        onOpenChange(false)
      }}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onOpenChange(false)
        }
      }}
    >
      <div className="mx-auto mt-[8vh] w-full max-w-lg rounded-xl bg-popover p-4 text-popover-foreground ring-1 ring-foreground/10">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h2 id={titleId} className="font-heading text-lg font-medium">
              {title}
            </h2>
            {description ? (
              <div className="mt-1 text-sm text-muted-foreground">
                {description}
              </div>
            ) : null}
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label="Fechar"
            onClick={() => {
              onOpenChange(false)
            }}
          >
            <XIcon />
          </Button>
        </div>
        {children}
      </div>
    </dialog>
  )
}
