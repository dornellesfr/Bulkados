import type { Copy } from '@/lib/api/copies'
import type { DeckCard } from '@/lib/api/decks'
import { personName } from '@/lib/api/schemas'

export type CopyAction =
  | 'take'
  | 'share'
  | 'remove'
  | 'request'
  | 'cancel'
  | 'refresh'
  | 'accept'
  | 'reject'
  | 'move'
  | 'return'
  | 'lock'
  | 'unlock'
  | 'groups'

export const copyActionLabel: Record<CopyAction, string> = {
  take: 'Selecionar',
  share: 'Compartilhar',
  remove: 'Remover',
  groups: 'Mudar bulks',
  request: 'Solicitar',
  cancel: 'Cancelar',
  refresh: 'Atualizar preço',
  accept: 'Aceitar',
  reject: 'Recusar',
  move: 'Mover',
  return: 'Devolver',
  lock: 'Travar',
  unlock: 'Destravar',
}

export type CopyActionPlan = {
  buttons: Array<CopyAction>
  menu: Array<CopyAction>
}

function withRefresh(
  buttons: Array<CopyAction>,
  menu: Array<CopyAction>,
  canRefresh: boolean,
): CopyActionPlan {
  if (!canRefresh) {
    return { buttons, menu }
  }

  if (buttons.length === 0 && menu.length === 0) {
    return { buttons: ['refresh'], menu: [] }
  }

  return { buttons, menu: [...menu, 'refresh'] }
}

export type BulkPrimary = 'select' | 'request' | 'unavailable'

export function bulkPrimary(copy: Copy, meId: string): BulkPrimary {
  if (copy.locked || copy.visibility === 'in_use_elsewhere') {
    return 'unavailable'
  }

  if (copy.visibility === 'in_deck' && copy.deck?.owner.id !== meId) {
    return 'request'
  }

  return 'select'
}

export function bulkPrimaryLabel(primary: BulkPrimary) {
  if (primary === 'request') {
    return 'Solicitar'
  }

  if (primary === 'select') {
    return 'Selecionar'
  }

  return 'Indisponível'
}

export function planBulkMenu(copy: Copy, meId: string): Array<CopyAction> {
  const mine = copy.holder.id === meId
  const addedByMe = copy.added_by.id === meId
  const menu: Array<CopyAction> = []

  if (mine && copy.state !== 'reserved') {
    menu.push('groups')
  }

  if (mine && copy.visibility === 'available') {
    menu.push('remove')
  }

  if (copy.open_request?.requester.id === meId) {
    menu.push('cancel')
  }

  if (
    (mine || addedByMe) &&
    !copy.catalog.is_basic &&
    copy.visibility !== 'in_use_elsewhere'
  ) {
    menu.push('refresh')
  }

  return menu
}

export function planDeckActions(
  card: DeckCard,
  meId: string,
  isOwner: boolean,
): CopyActionPlan {
  if (!isOwner) {
    return { buttons: [], menu: [] }
  }

  const canRefresh = card.holder.id === meId && !card.catalog.is_basic
  const incoming =
    card.open_request?.status === 'pending_acceptance' &&
    card.open_request.requester.id !== meId

  if (incoming) {
    return withRefresh(['accept', 'reject'], [], canRefresh)
  }

  if (!card.open_request) {
    return withRefresh(
      [card.locked ? 'unlock' : 'lock'],
      ['move', 'return', 'share'],
      canRefresh,
    )
  }

  return withRefresh([], [], canRefresh)
}

export function copyStateText(copy: Copy) {
  if (copy.visibility === 'available') {
    return {
      label: 'Livre',
      badge: null as string | null,
      detail: null as string | null,
    }
  }

  if (copy.visibility === 'reserved') {
    return {
      label: 'Indisponível',
      badge: null,
      detail: 'Pedido em análise',
    }
  }

  if (copy.visibility === 'in_use_elsewhere') {
    return {
      label: 'Indisponível',
      badge: null,
      detail: 'Em uso em outro grupo',
    }
  }

  return {
    label: copy.locked ? 'Travada' : 'Reservada',
    badge: null,
    detail: copy.deck
      ? `No deck de ${personName(copy.deck.owner)} · ${copy.deck.name}`
      : 'No deck',
  }
}
