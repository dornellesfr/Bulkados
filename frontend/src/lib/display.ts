import type { DeckFormat } from '@/lib/api/schemas'

const colorOrder = ['W', 'U', 'B', 'R', 'G'] as const

export const deckFormats: Array<{
  value: DeckFormat
  label: string
  hint: string
}> = [
  {
    value: 'commander_10',
    label: 'Commander 10',
    hint: 'até R$ 10 nas cartas e até R$ 5 na soma dos comandantes',
  },
  {
    value: 'commander_100',
    label: 'Commander 100',
    hint: 'teto de preço ainda não definido',
  },
  {
    value: 'commander_200',
    label: 'Commander 200',
    hint: 'teto de preço ainda não definido',
  },
  {
    value: 'commander_500',
    label: 'Commander 500',
    hint: 'teto de preço ainda não definido',
  },
  {
    value: 'competitive',
    label: 'Competitivo',
    hint: 'sem teto de preço',
  },
]

export function deckFormatLabel(format: DeckFormat) {
  return deckFormats.find((item) => item.value === format)?.label ?? format
}

export function formatColorIdentity(colors: string[]) {
  if (colors.length === 0) {
    return 'incolor'
  }

  const known = colorOrder.filter((color) => colors.includes(color))
  const rest = colors.filter(
    (color) => !colorOrder.includes(color as (typeof colorOrder)[number]),
  )

  return [...known, ...rest].join(' ')
}

export function sourceLabel(source: 'bulk' | 'deck') {
  return source === 'bulk' ? 'Bulk' : 'Deck'
}

export function safeInternalPath(value: string | undefined) {
  if (!value || !value.startsWith('/') || value.startsWith('//')) {
    return '/'
  }

  if (
    value.startsWith('/entrar') ||
    value.startsWith('/cadastrar') ||
    value.startsWith('/recuperar-senha')
  ) {
    return '/'
  }

  return value
}
