import { useEffect, useRef, useState } from 'react'

import { cn } from '@/lib/utils'

const PREVIEW_WIDTH = 320
const PREVIEW_HEIGHT = Math.round((PREVIEW_WIDTH * 680) / 488)
const GAP = 12
const MARGIN = 8

type Hover = { anchor: DOMRect; box: DOMRect }

// Dentro de um diálogo, a imagem vai ao lado dele, para não cobrir a lista.
function previewPosition({ anchor, box }: Hover) {
  const fitsRight =
    box.right + GAP + PREVIEW_WIDTH + MARGIN <= window.innerWidth
  const fitsLeft = box.left - GAP - PREVIEW_WIDTH >= MARGIN
  const left = fitsRight
    ? box.right + GAP
    : fitsLeft
      ? box.left - GAP - PREVIEW_WIDTH
      : Math.max(
          MARGIN,
          Math.min(
            anchor.right + GAP,
            window.innerWidth - PREVIEW_WIDTH - MARGIN,
          ),
        )
  const centered = anchor.top + anchor.height / 2 - PREVIEW_HEIGHT / 2
  const lowest = Math.max(MARGIN, window.innerHeight - PREVIEW_HEIGHT - MARGIN)

  return { left, top: Math.min(Math.max(MARGIN, centered), lowest) }
}

export function CardThumb({
  url,
  className,
}: {
  url: string | null
  className?: string
}) {
  const [hover, setHover] = useState<Hover | null>(null)
  const previewRef = useRef<HTMLImageElement>(null)

  useEffect(() => {
    if (hover) {
      previewRef.current?.showPopover()
    }
  }, [hover])

  if (!url) {
    return (
      <div className={cn('h-14 w-10 shrink-0 rounded bg-muted', className)} />
    )
  }

  const position = hover ? previewPosition(hover) : null

  return (
    <>
      <img
        src={url}
        alt=""
        loading="lazy"
        decoding="async"
        className={cn('h-14 w-10 shrink-0 rounded object-cover', className)}
        onMouseEnter={(event) => {
          const thumb = event.currentTarget
          const anchor = thumb.getBoundingClientRect()
          const dialogBox = thumb.closest('dialog')?.firstElementChild
          setHover({
            anchor,
            box: dialogBox ? dialogBox.getBoundingClientRect() : anchor,
          })
        }}
        onMouseLeave={() => {
          setHover(null)
        }}
      />
      {position ? (
        // popover: vai para a camada mais alta do navegador, acima até do diálogo aberto.
        <img
          ref={previewRef}
          popover="manual"
          src={url}
          alt=""
          className="pointer-events-none fixed m-0 overflow-visible rounded-[15px] border-0 bg-transparent p-0 shadow-2xl ring-1 ring-foreground/20"
          style={{
            inset: 'auto',
            left: position.left,
            top: position.top,
            width: PREVIEW_WIDTH,
          }}
        />
      ) : null}
    </>
  )
}
