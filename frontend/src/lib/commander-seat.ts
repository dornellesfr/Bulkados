import type { PartnerKind } from '@/lib/api/schemas'

export type CommanderFacts = {
  nameEn: string
  canBeCommander: boolean
  partnerKind: PartnerKind | null
  oracleText: string
  typeLine: string
  keywords: string[]
}

const partnerLabel: Record<PartnerKind, string> = {
  partner: 'Partner',
  partner_with: 'Partner with',
  friends_forever: 'Friends forever',
  background: 'Background',
  choose_a_background: 'Choose a Background',
  doctors_companion: "Doctor's companion",
}

export function commanderSeat(
  card: CommanderFacts,
  commanders: CommanderFacts[],
): { allowed: boolean; reason: string | null } {
  if (commanders.length >= 2) {
    return {
      allowed: false,
      reason: 'Este deck já tem dois comandantes.',
    }
  }

  if (commanders.length === 0) {
    if (card.canBeCommander) {
      return { allowed: true, reason: null }
    }

    if (card.partnerKind === 'background') {
      return {
        allowed: false,
        reason:
          'Um Background só entra como segundo comandante, ao lado de Choose a Background.',
      }
    }

    return {
      allowed: false,
      reason: 'Esta carta não pode ser comandante.',
    }
  }

  if (pairingIsValid(commanders[0], card)) {
    return { allowed: true, reason: null }
  }

  const name = commanders[0].nameEn

  if (card.partnerKind) {
    return {
      allowed: false,
      reason: `${partnerLabel[card.partnerKind]} desta carta não fecha dupla com ${name}.`,
    }
  }

  return {
    allowed: false,
    reason: `Esta carta não forma dupla com ${name}.`,
  }
}

export function cardsOutsideIdentity(
  colors: string[][],
  others: Array<{ nameEn: string; colorIdentity: string[] }>,
): string | null {
  const allowed = new Set(
    colors.flatMap((identity) => identity.map((color) => color.toUpperCase())),
  )
  const names = [
    ...new Set(
      others
        .filter(
          (card) =>
            !card.colorIdentity.every((color) =>
              allowed.has(color.toUpperCase()),
            ),
        )
        .map((card) => card.nameEn),
    ),
  ].sort()

  if (names.length === 0) {
    return null
  }

  const shown = names.slice(0, 3).join(', ')
  const rest = names.length - 3
  const suffix = rest > 0 ? ` e mais ${rest}` : ''

  return `Há cartas no deck fora da identidade de cor dos comandantes: ${shown}${suffix}.`
}

function pairingIsValid(left: CommanderFacts, right: CommanderFacts) {
  if (left.partnerKind === 'partner' && right.partnerKind === 'partner') {
    return true
  }

  if (
    left.partnerKind === 'friends_forever' &&
    right.partnerKind === 'friends_forever'
  ) {
    return true
  }

  if (
    left.partnerKind === 'partner_with' &&
    right.partnerKind === 'partner_with' &&
    namesPointAtEachOther(left, right)
  ) {
    return true
  }

  const kinds = new Set([left.partnerKind, right.partnerKind])

  if (kinds.has('choose_a_background') && kinds.has('background')) {
    return true
  }

  return isDoctorPair(left, right)
}

function isDoctorPair(left: CommanderFacts, right: CommanderFacts) {
  const leftIsDoctor = isDoctor(left.typeLine, left.keywords)
  const rightIsDoctor = isDoctor(right.typeLine, right.keywords)

  if (leftIsDoctor && right.partnerKind === 'doctors_companion') {
    return true
  }

  return rightIsDoctor && left.partnerKind === 'doctors_companion'
}

function isDoctor(typeLine: string, keywords: string[]) {
  const lowered = typeLine.toLowerCase()

  if (!lowered.includes('legendary') || !lowered.includes('creature')) {
    return false
  }

  if (keywords.some((keyword) => keyword.toLowerCase() === 'doctor')) {
    return true
  }

  return /\bDoctor\b/.test(typeLine)
}

function namesPointAtEachOther(left: CommanderFacts, right: CommanderFacts) {
  const leftTarget = partnerWithName(left.keywords, left.oracleText)
  const rightTarget = partnerWithName(right.keywords, right.oracleText)

  if (leftTarget == null || rightTarget == null) {
    return false
  }

  return (
    leftTarget.toLowerCase() === right.nameEn.toLowerCase() &&
    rightTarget.toLowerCase() === left.nameEn.toLowerCase()
  )
}

function partnerWithName(keywords: string[], oracleText: string) {
  for (const keyword of keywords) {
    const marker = 'partner with '

    if (keyword.toLowerCase().startsWith(marker)) {
      return keyword.slice(marker.length).trim()
    }
  }

  const match = /partner with\s+([^(\n]+)/i.exec(oracleText)

  if (!match?.[1]) {
    return null
  }

  return match[1].trim().replace(/\.+$/, '')
}
