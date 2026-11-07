import { useEffect, useId, useRef } from 'react'
import type { ReactNode } from 'react'
import { XIcon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  children,
  wide = false,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description?: ReactNode
  children: ReactNode
  wide?: boolean
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
      className="m-0 h-full max-h-none w-full max-w-none bg-transparent p-3 backdrop:bg-black/40 sm:p-6"
      onClose={() => {
        onOpenChange(false)
      }}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onOpenChange(false)
        }
      }}
    >
      <div
        className={cn(
          'mx-auto flex max-h-[calc(100dvh-1.5rem)] w-full flex-col overflow-hidden rounded-xl bg-popover text-popover-foreground ring-1 ring-foreground/10 sm:mt-[4vh] sm:max-h-[calc(100dvh-3rem)]',
          wide ? 'sm:w-[min(46rem,calc(100vw-3rem))]' : 'sm:max-w-lg',
        )}
      >
        <div className="flex shrink-0 items-start justify-between gap-3 border-b border-foreground/10 px-4 py-3 sm:px-5">
          <div className="min-w-0">
            <h2
              id={titleId}
              className="font-heading text-xl leading-snug font-medium"
            >
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
            className="shrink-0"
            aria-label="Fechar"
            onClick={() => {
              onOpenChange(false)
            }}
          >
            <XIcon />
          </Button>
        </div>
        <div className="min-h-0 overflow-auto px-4 py-4 sm:px-5">
          {children}
        </div>
      </div>
    </dialog>
  )
}
