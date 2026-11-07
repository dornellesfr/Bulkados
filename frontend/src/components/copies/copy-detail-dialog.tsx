import type { ReactNode } from 'react'

import { CardThumb } from '@/components/cards/card-thumb'
import { ColorIdentity } from '@/components/cards/color-identity'
import { ManaCost } from '@/components/cards/mana-cost'
import { CopyMark } from '@/components/copies/copy-mark'
import { Dialog } from '@/components/ui/dialog'
import type { Copy } from '@/lib/api/copies'
import { personName } from '@/lib/api/schemas'
import { copyStateText } from '@/lib/copy-actions'
import { isLegendary } from '@/lib/display'
import { formatCopyPrice } from '@/lib/money'

export function CopyDetailDialog({
  copy,
  onOpenChange,
  actions,
}: {
  copy: Copy | null
  onOpenChange: (open: boolean) => void
  actions?: ReactNode
}) {
  const name = copy ? (copy.catalog.name_pt ?? copy.catalog.name_en) : 'Carta'
  const state = copy ? copyStateText(copy) : null

  return (
    <Dialog open={copy != null} onOpenChange={onOpenChange} title={name} wide>
      {copy && state ? (
        <div className="flex flex-col gap-5 sm:grid sm:grid-cols-[minmax(0,20rem)_minmax(0,1fr)] sm:gap-6">
          <CardThumb
            url={copy.catalog.image_url}
            alt={name}
            preview={false}
            className="mx-auto aspect-[488/680] h-auto w-full max-w-72 rounded-[4.5%] object-cover sm:mx-0 sm:max-w-none"
          />
          <div className="sm:relative">
            <div className="flex flex-col gap-4 text-sm sm:absolute sm:inset-0">
              <div className="flex min-h-0 flex-col gap-4 sm:flex-1 sm:overflow-y-auto">
                <div className="flex flex-col gap-2">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex min-w-0 flex-col gap-1">
                      {copy.catalog.type_line ? (
                        <p>{copy.catalog.type_line}</p>
                      ) : null}
                      {isLegendary(copy.catalog.type_line) ? (
                        <p className="text-amber-800 dark:text-amber-300">
                          Lendária
                        </p>
                      ) : null}
                    </div>
                    <ManaCost
                      cost={copy.catalog.mana_cost}
                      className="shrink-0"
                      symbolClassName="size-5"
                    />
                  </div>
                  <ColorIdentity
                    colors={copy.catalog.color_identity}
                    name={null}
                  />
                </div>
                {copy.catalog.oracle_text ? (
                  <div className="rounded-lg bg-muted/70 px-3 py-3 leading-relaxed whitespace-pre-line ring-1 ring-foreground/10">
                    {copy.catalog.oracle_text}
                  </div>
                ) : null}
                <div className="flex flex-col gap-1">
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                    <CopyMark copy={copy} />
                    {state.detail ? (
                      <span className="text-muted-foreground">
                        {state.detail}
                      </span>
                    ) : null}
                  </div>
                  {copy.visibility === 'in_use_elsewhere' ? null : (
                    <p className="text-muted-foreground">
                      Casa {personName(copy.holder)}
                    </p>
                  )}
                  <p className="text-muted-foreground">
                    {formatCopyPrice(copy.price_cents, copy.catalog.is_basic)}
                  </p>
                </div>
              </div>
              {actions ? (
                <div className="flex shrink-0 justify-end">{actions}</div>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </Dialog>
  )
}
