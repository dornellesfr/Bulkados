import type { ReactNode } from 'react'
import {
  BellRingIcon,
  CheckIcon,
  CrownIcon,
  LockIcon,
  LockOpenIcon,
  RefreshCwIcon,
  Trash2Icon,
  XIcon,
} from 'lucide-react'

import { CardThumb } from '@/components/cards/card-thumb'
import { ColorIdentity, colorNames } from '@/components/cards/color-identity'
import { ManaCost } from '@/components/cards/mana-cost'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import type { DeckCard } from '@/lib/api/decks'
import { personName } from '@/lib/api/schemas'
import { formatCopyPrice } from '@/lib/money'

const partnerLabels: Record<string, string> = {
  partner: 'Partner',
  partner_with: 'Partner with',
  friends_forever: 'Friends forever',
  background: 'Background',
  choose_a_background: 'Choose a Background',
  doctors_companion: "Doctor's companion",
}

const legalLabels: Record<DeckCard['catalog']['commander_legal'], string> = {
  legal: 'Legal',
  banned: 'Banida',
  not_legal: 'Fora do Commander',
}

function colorNamesText(colors: Array<string>) {
  return colors.length === 0
    ? 'Incolor'
    : colors.map((color) => colorNames[color] ?? color).join(', ')
}

function Detail({ label, children }: { label: string; children: ReactNode }) {
  return (
    <>
      <dt className="text-muted-foreground">{label}</dt>
      <dd>{children}</dd>
    </>
  )
}

export function DeckCardDialog({
  card,
  meId,
  isOwner,
  busy,
  warnings,
  onOpenChange,
  onReturn,
  onToggleCommander,
  onToggleLock,
  onRefresh,
  onAccept,
  onReject,
}: {
  card: DeckCard | null
  meId: string
  isOwner: boolean
  busy: boolean
  warnings: Array<string>
  onOpenChange: (open: boolean) => void
  onReturn: (card: DeckCard) => void
  onToggleCommander: (card: DeckCard) => void
  onToggleLock: (card: DeckCard) => void
  onRefresh: (card: DeckCard) => void
  onAccept: (card: DeckCard) => void
  onReject: (card: DeckCard) => void
}) {
  const name = card ? (card.catalog.name_pt ?? card.catalog.name_en) : 'Carta'
  const pending = card?.open_request ?? null
  const awaitingDecision = pending?.status === 'pending_acceptance'
  const canRefresh =
    card != null && card.holder.id === meId && !card.catalog.is_basic

  return (
    <Dialog open={card != null} onOpenChange={onOpenChange} title={name} wide>
      {card ? (
        <div className="flex flex-col gap-5 sm:grid sm:grid-cols-[minmax(0,18rem)_minmax(0,1fr)] sm:gap-6">
          <CardThumb
            url={card.catalog.image_url}
            alt={name}
            preview={false}
            className="mx-auto aspect-[488/680] h-auto w-full max-w-64 rounded-[4.5%] object-cover sm:mx-0 sm:max-w-none"
          />
          <div className="flex min-w-0 flex-col gap-4 text-sm">
            <div className="flex flex-col gap-2">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-heading text-lg font-medium">
                    {card.catalog.name_pt ?? card.catalog.name_en}
                  </p>
                  {card.catalog.name_pt ? (
                    <p className="text-muted-foreground">
                      {card.catalog.name_en}
                    </p>
                  ) : null}
                </div>
                <ManaCost
                  cost={card.catalog.mana_cost}
                  className="shrink-0"
                  symbolClassName="size-5"
                />
              </div>
              <ColorIdentity colors={card.catalog.color_identity} name={null} />
              <p className="text-muted-foreground">{card.catalog.type_line}</p>
            </div>

            {pending ? (
              <div className="flex flex-col gap-1 rounded-lg bg-amber-500/10 px-3 py-2 text-amber-900 ring-1 ring-amber-500/30 dark:text-amber-200">
                <p className="flex items-center gap-2 font-medium">
                  <BellRingIcon className="size-4 shrink-0" />
                  Pedido de {personName(pending.requester)}
                </p>
                <p className="text-xs">
                  {awaitingDecision
                    ? 'A carta está reservada. Aceite para seguir para o encontro ou recuse para mantê-la no deck.'
                    : 'Pedido aceito. A carta só muda de mão quando os dois confirmarem no encontro.'}
                </p>
              </div>
            ) : null}

            {warnings.length > 0 ? (
              <ul className="flex flex-col gap-1 rounded-lg bg-destructive/10 px-3 py-2 text-destructive">
                {warnings.map((warning, index) => (
                  <li key={`${warning}-${index}`}>{warning}</li>
                ))}
              </ul>
            ) : null}

            {card.catalog.oracle_text ? (
              <div className="rounded-lg bg-muted/70 px-3 py-3 leading-relaxed whitespace-pre-line ring-1 ring-foreground/10">
                {card.catalog.oracle_text}
              </div>
            ) : null}

            <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-2">
              <Detail label="Cores">
                {colorNamesText(card.catalog.color_identity)}
              </Detail>
              <Detail label="Casa">{personName(card.holder)}</Detail>
              <Detail label="Preço">
                {formatCopyPrice(card.price_cents, card.catalog.is_basic)}
              </Detail>
              <Detail label="No deck">
                {card.role === 'commander' ? 'Comandante' : 'Carta comum'}
              </Detail>
              <Detail label="Trava">
                {card.locked ? 'Travada' : 'Destravada'}
              </Detail>
              <Detail label="Commander">
                {legalLabels[card.catalog.commander_legal]}
              </Detail>
              {card.catalog.partner_kind ? (
                <Detail label="Parceria">
                  {partnerLabels[card.catalog.partner_kind] ??
                    card.catalog.partner_kind}
                </Detail>
              ) : null}
              {card.catalog.keywords.length > 0 ? (
                <Detail label="Palavras-chave">
                  {card.catalog.keywords.join(', ')}
                </Detail>
              ) : null}
              {card.catalog.is_basic ? (
                <Detail label="Terreno básico">
                  <Badge variant="secondary">Sim</Badge>
                </Detail>
              ) : null}
            </dl>

            {isOwner ? (
              <div className="flex flex-wrap items-center justify-end gap-2 border-t border-foreground/10 pt-4">
                {pending && awaitingDecision ? (
                  <>
                    <Button
                      type="button"
                      variant="outline"
                      disabled={busy}
                      onClick={() => {
                        onReject(card)
                      }}
                    >
                      <XIcon />
                      Recusar
                    </Button>
                    <Button
                      type="button"
                      disabled={busy}
                      onClick={() => {
                        onAccept(card)
                      }}
                    >
                      <CheckIcon />
                      Aceitar
                    </Button>
                  </>
                ) : null}
                {!pending ? (
                  <>
                    <Button
                      type="button"
                      variant="outline"
                      disabled={busy}
                      onClick={() => {
                        onToggleLock(card)
                      }}
                    >
                      {card.locked ? <LockOpenIcon /> : <LockIcon />}
                      {card.locked ? 'Destravar' : 'Travar para o deck'}
                    </Button>
                    {card.role === 'commander' && card.can_toggle_commander ? (
                      <Button
                        type="button"
                        variant="outline"
                        disabled={busy}
                        onClick={() => {
                          onToggleCommander(card)
                        }}
                      >
                        <CrownIcon />
                        Remover de comandante
                      </Button>
                    ) : null}
                    {canRefresh ? (
                      <Button
                        type="button"
                        variant="outline"
                        disabled={busy}
                        onClick={() => {
                          onRefresh(card)
                        }}
                      >
                        <RefreshCwIcon />
                        Atualizar preço
                      </Button>
                    ) : null}
                    <Button
                      type="button"
                      variant="destructive"
                      disabled={busy}
                      onClick={() => {
                        onReturn(card)
                      }}
                    >
                      <Trash2Icon />
                      Remover do deck
                    </Button>
                  </>
                ) : null}
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
    </Dialog>
  )
}
