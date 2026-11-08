import type { DeckBulkCard, DeckCard, DeckDetail } from '@/lib/api/decks'
import type { DeckFormat } from '@/lib/api/schemas'

export type DeckCardCategory =
  | 'commander'
  | 'creature'
  | 'planeswalker'
  | 'battle'
  | 'instant'
  | 'sorcery'
  | 'enchantment'
  | 'artifact'
  | 'land'
  | 'other'

export const deckCategoryOrder: Array<DeckCardCategory> = [
  'commander',
  'creature',
  'planeswalker',
  'battle',
  'instant',
  'sorcery',
  'enchantment',
  'artifact',
  'land',
  'other',
]

const categoryLabels: Record<DeckCardCategory, [string, string]> = {
  commander: ['Comandante', 'Comandantes'],
  creature: ['Criatura', 'Criaturas'],
  planeswalker: ['Planeswalker', 'Planeswalkers'],
  battle: ['Batalha', 'Batalhas'],
  instant: ['Instantânea', 'Instantâneas'],
  sorcery: ['Feitiço', 'Feitiços'],
  enchantment: ['Encantamento', 'Encantamentos'],
  artifact: ['Artefato', 'Artefatos'],
  land: ['Terreno', 'Terrenos'],
  other: ['Outra carta', 'Outras cartas'],
}

export function deckCategoryLabel(category: DeckCardCategory, count: number) {
  const [singular, plural] = categoryLabels[category]
  return count === 1 ? singular : plural
}

export function deckCardCategory(card: DeckCard): DeckCardCategory {
  if (card.role === 'commander') {
    return 'commander'
  }

  const typeLine = (card.catalog.type_line ?? '').toLocaleLowerCase('en')
  const has = (type: string) => typeLine.includes(type)

  if (has('creature')) {
    return 'creature'
  }

  if (has('planeswalker')) {
    return 'planeswalker'
  }

  if (has('battle')) {
    return 'battle'
  }

  if (has('instant')) {
    return 'instant'
  }

  if (has('sorcery')) {
    return 'sorcery'
  }

  if (has('enchantment')) {
    return 'enchantment'
  }

  if (has('artifact')) {
    return 'artifact'
  }

  if (has('land')) {
    return 'land'
  }

  return 'other'
}

export function groupDeckCards(cards: Array<DeckCard>) {
  const grouped = new Map<DeckCardCategory, Array<DeckCard>>()

  for (const card of cards) {
    const category = deckCardCategory(card)
    const bucket = grouped.get(category) ?? []
    bucket.push(card)
    grouped.set(category, bucket)
  }

  return deckCategoryOrder.flatMap((category) => {
    const bucket = grouped.get(category)

    if (!bucket || bucket.length === 0) {
      return []
    }

    return [{ category, cards: bucket }]
  })
}

export function splitDeckColumns(sections: ReturnType<typeof groupDeckCards>) {
  const columns: [typeof sections, typeof sections] = [[], []]
  const sizes = [0, 0]

  for (const section of sections) {
    const target = sizes[0] <= sizes[1] ? 0 : 1
    columns[target].push(section)
    sizes[target] += section.cards.length + 1
  }

  return columns
}

export function deckBudgetCapCents(format: DeckFormat) {
  const caps: Partial<Record<DeckFormat, number>> = {
    commander_10: 1000,
    commander_100: 10000,
    commander_200: 20000,
    commander_500: 50000,
  }

  return caps[format] ?? null
}

function cardName(card: DeckCard) {
  return card.catalog.name_pt ?? card.catalog.name_en
}

export function buildBulkText(deck: DeckDetail) {
  return groupDeckCards(deck.cards)
    .map((section) => {
      const heading = deckCategoryLabel(section.category, section.cards.length)
      const lines = section.cards.map((card) => `1x ${cardName(card)}`)
      return [`# ${heading}`, ...lines].join('\n')
    })
    .join('\n\n')
}

function cleanBulkLine(line: string) {
  return line
    .replace(/(?:\s+\*[A-Z0-9]+\*)+\s*$/i, '')
    .replace(
      /\s+\([A-Z0-9]{2,6}\)(?:\s+[A-Z0-9]+(?:-[A-Z0-9]+)*[a-z]?)?\s*$/,
      '',
    )
    .replace(
      /\s+\[[A-Z0-9]{2,6}\](?:\s+[A-Z0-9]+(?:-[A-Z0-9]+)*[a-z]?)?\s*$/,
      '',
    )
    .trim()
}

export function parseBulkText(text: string): Array<DeckBulkCard> {
  let role: DeckBulkCard['role'] = 'main'
  const cards: Array<DeckBulkCard> = []

  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim()

    if (line === '') {
      continue
    }

    const heading = line.match(/^(?:#+|\/\/+)\s*(.*)$/)

    if (heading) {
      role = /comandante|commander/i.test(heading[1]) ? 'commander' : 'main'
      continue
    }

    const quantity = line.match(/^(\d+)\s*[xX]?\s+(.+)$/)
    const count = quantity ? Number.parseInt(quantity[1], 10) : 1
    const name = cleanBulkLine(quantity ? quantity[2] : line)

    if (name === '') {
      continue
    }

    for (let index = 0; index < count; index += 1) {
      cards.push({ name, role })
    }
  }

  return cards
}
