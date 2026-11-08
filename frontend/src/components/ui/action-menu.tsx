import { useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { EllipsisIcon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

type Anchor = {
  top: number
  left: number
  width: number
  height: number
}

export function ActionMenu({
  items,
}: {
  items: Array<{
    id: string
    label: string
    destructive?: boolean
    onSelect: () => void
  }>
}) {
  const [open, setOpen] = useState(false)
  const [anchor, setAnchor] = useState<Anchor | null>(null)
  const rootRef = useRef<HTMLDivElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)
  const menuId = useId()

  useEffect(() => {
    if (!open) {
      return
    }

    const place = () => {
      const rect = buttonRef.current?.getBoundingClientRect()

      if (!rect) {
        return
      }

      setAnchor({
        top: rect.top,
        left: rect.left,
        width: rect.width,
        height: rect.height,
      })
    }

    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as Node

      if (
        rootRef.current?.contains(target) ||
        menuRef.current?.contains(target)
      ) {
        return
      }

      setOpen(false)
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false)
      }
    }

    place()
    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    window.addEventListener('resize', place)
    window.addEventListener('scroll', place, true)

    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
      window.removeEventListener('resize', place)
      window.removeEventListener('scroll', place, true)
    }
  }, [open])

  if (items.length === 0) {
    return null
  }

  const openUp =
    anchor != null && window.innerHeight - (anchor.top + anchor.height) < 200
  const layer = buttonRef.current?.closest('dialog') ?? document.body
  const menu =
    open && anchor
      ? createPortal(
          <div
            ref={menuRef}
            id={menuId}
            role="menu"
            className="fixed z-50 min-w-44 rounded-lg bg-popover p-1 text-popover-foreground shadow-md ring-1 ring-foreground/10"
            style={{
              top: openUp ? anchor.top - 4 : anchor.top + anchor.height + 4,
              left: Math.max(8, anchor.left + anchor.width - 176),
              transform: openUp ? 'translateY(-100%)' : undefined,
            }}
          >
            {items.map((item) => (
              <button
                key={item.id}
                type="button"
                role="menuitem"
                className={cn(
                  'flex w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-muted',
                  item.destructive && 'text-destructive',
                )}
                onClick={() => {
                  setOpen(false)
                  item.onSelect()
                }}
              >
                {item.label}
              </button>
            ))}
          </div>,
          layer,
        )
      : null

  return (
    <div ref={rootRef} className="relative">
      <Button
        ref={buttonRef}
        type="button"
        variant="outline"
        size="icon"
        aria-label="Mais opções"
        aria-expanded={open}
        aria-haspopup="menu"
        aria-controls={menuId}
        onClick={() => {
          setOpen((current) => !current)
        }}
      >
        <EllipsisIcon />
      </Button>
      {menu}
    </div>
  )
}
