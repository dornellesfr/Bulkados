import { Fragment } from 'react'

import { cn } from '@/lib/utils'

const specialFiles: Record<string, string> = { '½': 'HALF', '∞': 'INFINITY' }

function symbolUrl(symbol: string) {
  const inner = symbol.slice(1, -1)
  const file = specialFiles[inner] ?? inner.replace(/\//g, '')
  return `https://svgs.scryfall.io/card-symbols/${file}.svg`
}

export function ManaCost({
  cost,
  className,
}: {
  cost: string | null
  className?: string
}) {
  if (!cost) {
    return null
  }

  const faces = cost.split(/\s*\/\/\s*|\n/).filter(Boolean)

  return (
    <span
      title={cost}
      className={cn(
        'inline-flex flex-wrap items-center gap-x-1.5 gap-y-1',
        className,
      )}
    >
      {faces.map((face, faceIndex) => (
        <Fragment key={`${face}-${faceIndex}`}>
          {faceIndex > 0 ? (
            <span className="text-muted-foreground">//</span>
          ) : null}
          <span className="inline-flex items-center gap-0.5">
            {(face.match(/\{[^}]+\}/g) ?? []).map((symbol, index) => (
              <img
                key={`${symbol}-${index}`}
                src={symbolUrl(symbol)}
                alt={symbol}
                className="size-4"
              />
            ))}
          </span>
        </Fragment>
      ))}
    </span>
  )
}
