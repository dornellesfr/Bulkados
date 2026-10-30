import type { Copy } from '@/lib/api/copies'
import type { DeckCard } from '@/lib/api/decks'

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

export const copyActionLabel: Record<CopyAction, string> = {
  take: 'Pegar na hora',
  share: 'Compartilhar',
  remove: 'Remover',
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

export function planBulkActions(copy: Copy, meId: string): CopyActionPlan {
  if (copy.visibility === 'in_use_elsewhere') {
    return { buttons: [], menu: [] }
  }

  const mine = copy.holder.id === meId
  const addedByMe = copy.added_by.id === meId
  const otherLockedDeck =
    copy.visibility === 'in_deck' &&
    copy.deck != null &&
    copy.deck.owner.id !== meId &&
    copy.locked
  const canRefresh =
    (mine || addedByMe) && !copy.catalog.is_basic && !otherLockedDeck

  if (otherLockedDeck) {
    return { buttons: [], menu: [] }
  }

  if (copy.visibility === 'reserved') {
    const buttons: Array<CopyAction> =
      copy.open_request?.requester.id === meId ? ['cancel'] : []
    return withRefresh(buttons, [], canRefresh)
  }

  if (copy.visibility === 'available' && mine) {
    return withRefresh(['take'], ['share', 'remove'], canRefresh)
  }

  if (copy.visibility === 'available') {
    return withRefresh(['request'], [], canRefresh)
  }

  if (copy.deck && copy.deck.owner.id !== meId) {
    if (!copy.locked) {
      return withRefresh(['request'], [], canRefresh)
    }

    return { buttons: [], menu: [] }
  }

  if (copy.deck?.owner.id === meId) {
    const incoming =
      copy.open_request?.status === 'pending_acceptance' &&
      copy.open_request.requester.id !== meId

    if (incoming) {
      return withRefresh(['accept', 'reject'], [], canRefresh)
    }

    if (!copy.open_request) {
      return withRefresh(
        [copy.locked ? 'unlock' : 'lock'],
        ['move', 'return', 'share'],
        canRefresh,
      )
    }
  }

  return withRefresh([], [], canRefresh)
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
    return { label: 'Reservada', badge: null, detail: null }
  }

  if (copy.visibility === 'in_use_elsewhere') {
    return { label: 'Em uso em outro grupo', badge: null, detail: null }
  }

  const nick = copy.deck?.owner.nick
  return {
    label: nick ? `No deck de ${nick}` : 'No deck',
    badge: copy.locked ? 'Travada' : 'Destravada',
    detail: copy.deck?.name ?? null,
  }
}
