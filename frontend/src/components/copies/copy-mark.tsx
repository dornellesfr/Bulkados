import { BanIcon, BookmarkIcon, CircleCheckIcon, LockIcon } from 'lucide-react'

import type { Copy } from '@/lib/api/copies'
import { cn } from '@/lib/utils'

const marks = {
  livre: {
    label: 'Livre',
    Icon: CircleCheckIcon,
    tone: 'text-emerald-700 dark:text-emerald-300',
  },
  reservada: {
    label: 'Reservada',
    Icon: BookmarkIcon,
    tone: 'text-sky-700 dark:text-sky-300',
  },
  indisponivel: {
    label: 'Indisponível',
    Icon: BanIcon,
    tone: 'text-muted-foreground',
  },
  travada: {
    label: 'Travada',
    Icon: LockIcon,
    tone: 'text-amber-700 dark:text-amber-300',
  },
} as const

export type CopyMarkKind = keyof typeof marks

export function copyMark(copy: Copy): CopyMarkKind {
  if (
    copy.visibility === 'reserved' ||
    copy.visibility === 'in_use_elsewhere'
  ) {
    return 'indisponivel'
  }

  if (copy.locked) {
    return 'travada'
  }

  if (copy.visibility === 'available') {
    return 'livre'
  }

  return 'reservada'
}

type Mark = (typeof marks)[CopyMarkKind]

function markOf(kind: CopyMarkKind): Mark {
  return marks[kind]
}

export function CopyMark({
  copy,
  className,
}: {
  copy: Copy
  className?: string
}) {
  const kind = copyMark(copy)

  const { label, Icon, tone } = markOf(kind)

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 font-medium',
        tone,
        className,
      )}
    >
      <Icon className="size-4 shrink-0" />
      {label}
    </span>
  )
}

export function CopyMarkBadge({ copy }: { copy: Copy }) {
  const kind = copyMark(copy)

  const { label, Icon, tone } = markOf(kind)

  return (
    <span
      title={label}
      className={cn(
        'pointer-events-none absolute top-4 right-4 z-10 flex size-8 items-center justify-center rounded-full bg-background/90 ring-1 ring-foreground/15',
        tone,
      )}
    >
      <Icon className="size-4" />
      <span className="sr-only">{label}</span>
    </span>
  )
}
